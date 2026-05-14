import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, cast

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.crud import (
    get_checkpoint,
    get_spot_order_by_binance_id,
    save_cancel_log,
    save_or_update_checkpoint,
    save_order_status_log,
    save_spot_order,
    update_spot_order_status,
)
from app.models.ai import ResumeCommandPayload
from app.models.requests import CancelOrderRequest, SpotOrderRequest
from app.models.responses import CancelOrderResponse, OrderRunResponse, OrderStatusResponse
from app.services import ai_gateway_service
from app.services.binance_auth_service import build_signed_params
from app.services.report_service import save_run_report

logger = logging.getLogger(__name__)

_ALLOWED_SYMBOLS = {"BTCUSDT", "ETHUSDT"}
_MAX_QUOTE_ORDER_QTY = "50"


def _build_request_context(run_id: str, req: SpotOrderRequest) -> dict[str, Any]:
    user_input: dict[str, Any] = {
        "symbol": req.symbol,
        "side": req.side,
        "type": req.type,
    }
    if req.quantity:
        user_input["quantity"] = req.quantity
    if req.quote_order_qty:
        user_input["quoteOrderQty"] = req.quote_order_qty
    if req.price:
        user_input["price"] = req.price
    if req.time_in_force:
        user_input["timeInForce"] = req.time_in_force
    return {
        "request_id": run_id,
        "request_type": "PLACE_ORDER_TEST",
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "user_input": user_input,
    }


def _build_policy_context(symbol: str) -> dict[str, Any]:
    return {
        "policy_refs": ["policy.symbol_allowlist", "policy.spot_testnet_only"],
        "applied_rules": {
            "allowed_symbols": list(_ALLOWED_SYMBOLS),
            "max_quote_order_qty": _MAX_QUOTE_ORDER_QTY,
        },
    }


def _extract_reason_codes(ai_state: dict[str, Any], stage: str) -> list[str]:
    return ai_state.get("decision_trace", {}).get(stage, {}).get("reason_codes", [])


def _user_input_to_request(user_input: dict[str, Any]) -> SpotOrderRequest:
    return SpotOrderRequest.model_construct(
        symbol=user_input.get("symbol", ""),
        side=user_input.get("side", "BUY"),
        type=user_input.get("type", "MARKET"),
        quantity=user_input.get("quantity"),
        quote_order_qty=user_input.get("quoteOrderQty"),
        price=user_input.get("price"),
        time_in_force=user_input.get("timeInForce"),
    )


def _apply_resume_patch_fields(
    user_input: dict[str, Any],
    patch_fields: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(user_input)

    supplemental = patch_fields.get("supplemental_user_input")
    if isinstance(supplemental, dict):
        merged.update(supplemental)

    approval = patch_fields.get("approval")
    if isinstance(approval, dict) and approval.get("approved") is True:
        merged["requires_review"] = False

    return merged


async def _fetch_account(settings: Settings) -> dict[str, Any]:
    signed = build_signed_params(settings.binance_testnet_secret_key, {})
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.binance_testnet_rest_base_url}/v3/account",
            headers={"X-MBX-APIKEY": settings.binance_testnet_api_key},
            params=signed,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()


async def _revalidate(req: SpotOrderRequest, settings: Settings) -> dict[str, Any] | None:
    reason_codes: list[str] = []

    if req.symbol not in _ALLOWED_SYMBOLS:
        return {"reason_codes": ["SYMBOL_NOT_ALLOWED"], "notes": "Symbol not in allowlist"}

    base_asset = req.symbol.replace("USDT", "")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.binance_testnet_rest_base_url}/v3/exchangeInfo",
                params={"symbol": req.symbol},
                timeout=10,
            )
            resp.raise_for_status()
            info = resp.json()
        sym_info = next((s for s in info.get("symbols", []) if s["symbol"] == req.symbol), None)
        if sym_info:
            base_asset = sym_info.get("baseAsset", base_asset)
            filters = {f["filterType"]: f for f in sym_info.get("filters", [])}
            if req.type == "LIMIT" and req.quantity and req.price:
                try:
                    qty = Decimal(req.quantity)
                    price = Decimal(req.price)
                    lot = filters.get("LOT_SIZE", {})
                    min_qty = Decimal(lot.get("minQty", "0"))
                    if min_qty > 0 and qty < min_qty:
                        reason_codes.append("LOT_SIZE_VIOLATED")
                    mn = filters.get("MIN_NOTIONAL") or filters.get("NOTIONAL", {})
                    min_notional = Decimal(mn.get("minNotional", "0"))
                    if min_notional > 0 and qty * price < min_notional:
                        reason_codes.append("MIN_NOTIONAL_NOT_MET")
                except InvalidOperation:
                    reason_codes.append("INVALID_ORDER_PARAMS")
    except Exception:
        logger.exception("exchangeInfo fetch failed during revalidation")
        reason_codes.append("EXCHANGE_INFO_UNAVAILABLE")

    try:
        account = await _fetch_account(settings)
        balances = {b["asset"]: Decimal(b["free"]) for b in account.get("balances", [])}
        if req.side == "BUY":
            if req.quote_order_qty:
                needed = Decimal(req.quote_order_qty)
                if balances.get("USDT", Decimal("0")) < needed:
                    reason_codes.append("INSUFFICIENT_BALANCE")
            elif req.quantity and req.price:
                needed = Decimal(req.quantity) * Decimal(req.price)
                if balances.get("USDT", Decimal("0")) < needed:
                    reason_codes.append("INSUFFICIENT_BALANCE")
        elif req.side == "SELL" and req.quantity:
            needed = Decimal(req.quantity)
            if balances.get(base_asset, Decimal("0")) < needed:
                reason_codes.append("INSUFFICIENT_BALANCE")
    except Exception:
        logger.exception("Account balance check failed during revalidation")

    if reason_codes:
        return {"reason_codes": reason_codes, "notes": "Deterministic revalidation blocked the order before submit."}
    return None


async def _submit_to_binance(req: SpotOrderRequest, settings: Settings) -> dict[str, Any]:
    params: dict[str, Any] = {
        "symbol": req.symbol,
        "side": req.side,
        "type": req.type,
    }
    if req.quantity:
        params["quantity"] = req.quantity
    if req.quote_order_qty:
        params["quoteOrderQty"] = req.quote_order_qty
    if req.price:
        params["price"] = req.price
    if req.time_in_force:
        params["timeInForce"] = req.time_in_force
    signed = build_signed_params(settings.binance_testnet_secret_key, params)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.binance_testnet_rest_base_url}/v3/order",
            headers={"X-MBX-APIKEY": settings.binance_testnet_api_key},
            params=signed,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()


async def _execute_order(
    db: Session,
    run_id: str,
    req: SpotOrderRequest,
    ai_state: dict[str, Any],
    settings: Settings,
) -> OrderRunResponse:
    rejection = await _revalidate(req, settings)
    if rejection:
        final_state = ai_state
        try:
            final_state = await ai_gateway_service.send_completion(
                run_id, {"be_rejection_evidence": rejection}, settings
            )
        except Exception:
            logger.exception("send_completion(BE_REJECTED) failed for run_id=%s", run_id)

        report_json = final_state.get("report", {})
        if report_json or final_state.get("lifecycle_status") == "BE_REJECTED":
            save_run_report(
                db,
                run_id=run_id,
                ai_state=final_state,
                order_id=None,
                fallback_reason_codes=rejection["reason_codes"],
            )

        save_or_update_checkpoint(
            db,
            run_id,
            final_state.get("lifecycle_status", "BE_REJECTED"),
            final_state.get("hold_reason"),
            final_state,
        )
        return OrderRunResponse(
            run_id=run_id,
            lifecycle_status=final_state.get("lifecycle_status", "BE_REJECTED"),
            reason_codes=rejection["reason_codes"],
        )

    try:
        binance_resp = await _submit_to_binance(req, settings)
    except httpx.HTTPStatusError as e:
        logger.error("Binance order submit failed: %s %s", e.response.status_code, e.response.text)
        rej: dict[str, Any] = {"reason_codes": ["BINANCE_SUBMIT_FAILED"], "notes": e.response.text}
        try:
            await ai_gateway_service.send_completion(run_id, {"be_rejection_evidence": rej}, settings)
        except Exception:
            pass
        raise HTTPException(status_code=502, detail="Binance order submission failed")
    except Exception:
        logger.exception("Unexpected Binance submit error for run_id=%s", run_id)
        rej = {"reason_codes": ["BINANCE_SUBMIT_FAILED"], "notes": "Unexpected error"}
        try:
            await ai_gateway_service.send_completion(run_id, {"be_rejection_evidence": rej}, settings)
        except Exception:
            pass
        raise HTTPException(status_code=502, detail="Binance order submission failed")

    binance_order_id = str(binance_resp.get("orderId", ""))
    order_row = save_spot_order(
        db,
        symbol=req.symbol,
        request_json=req.model_dump(),
        response_json=binance_resp,
        binance_order_id=binance_order_id,
        status=binance_resp.get("status", "NEW"),
    )

    execution_result: dict[str, Any] = {
        "status": binance_resp.get("status", ""),
        "orderId": binance_resp.get("orderId"),
        "clientOrderId": binance_resp.get("clientOrderId", ""),
    }
    try:
        final_state = await ai_gateway_service.send_completion(run_id, {"execution_result": execution_result}, settings)
    except Exception:
        logger.exception("send_completion(execution_result) failed for run_id=%s", run_id)
        final_state = ai_state

    save_run_report(
        db,
        run_id=run_id,
        ai_state=final_state,
        order_id=order_row.order_id,
        order_outcome=binance_resp,
    )
    save_or_update_checkpoint(db, run_id, final_state.get("lifecycle_status", "REPORT_READY"), None, final_state)

    return OrderRunResponse(
        run_id=run_id,
        lifecycle_status=final_state.get("lifecycle_status", "REPORT_READY"),
        order_id=binance_resp.get("orderId"),
        symbol=binance_resp.get("symbol"),
        status=binance_resp.get("status"),
        type=binance_resp.get("type"),
        side=binance_resp.get("side"),
    )


async def _process_lifecycle(
    db: Session,
    run_id: str,
    req: SpotOrderRequest,
    ai_state: dict[str, Any],
    lifecycle: str,
    settings: Settings,
) -> OrderRunResponse:
    if lifecycle == "READY_FOR_BE":
        return await _execute_order(db, run_id, req, ai_state, settings)
    if lifecycle == "HOLD":
        save_run_report(db, run_id=run_id, ai_state=ai_state)
        return OrderRunResponse(
            run_id=run_id,
            lifecycle_status="HOLD",
            hold_reason=ai_state.get("hold_reason"),
        )
    if lifecycle == "NO_ORDER":
        save_run_report(db, run_id=run_id, ai_state=ai_state)
        return OrderRunResponse(
            run_id=run_id,
            lifecycle_status="NO_ORDER",
            reason_codes=_extract_reason_codes(ai_state, "risk"),
        )
    logger.error("Unexpected AI lifecycle=%s for run_id=%s", lifecycle, run_id)
    raise HTTPException(status_code=500, detail=f"AI run failed: lifecycle={lifecycle}")


async def create_order(db: Session, req: SpotOrderRequest, settings: Settings) -> OrderRunResponse:
    run_id = f"run_{uuid.uuid4().hex}"
    request_context = _build_request_context(run_id, req)
    policy_context = _build_policy_context(req.symbol)

    try:
        ai_state = await ai_gateway_service.start_run(run_id, request_context, policy_context, settings)
    except Exception:
        logger.exception("AI start_run failed for run_id=%s", run_id)
        raise HTTPException(status_code=500, detail="AI service unavailable")

    lifecycle = ai_state.get("lifecycle_status", "FAILED")
    save_or_update_checkpoint(db, run_id, lifecycle, ai_state.get("hold_reason"), ai_state)
    return await _process_lifecycle(db, run_id, req, ai_state, lifecycle, settings)


async def resume_order(db: Session, payload: ResumeCommandPayload, settings: Settings) -> OrderRunResponse:
    checkpoint = get_checkpoint(db, payload.run_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail=f"run_id not found: {payload.run_id}")
    if checkpoint.lifecycle_status != "HOLD":
        raise HTTPException(
            status_code=400,
            detail=f"Only HOLD runs can be resumed, current status: {checkpoint.lifecycle_status}",
        )
    if checkpoint.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Checkpoint has expired")

    try:
        ai_state = await ai_gateway_service.resume_run(payload.run_id, payload.resume_reason, payload.patch_fields, settings)
    except Exception:
        logger.exception("AI resume_run failed for run_id=%s", payload.run_id)
        raise HTTPException(status_code=500, detail="AI service unavailable")

    lifecycle = ai_state.get("lifecycle_status", "FAILED")
    save_or_update_checkpoint(db, payload.run_id, lifecycle, ai_state.get("hold_reason"), ai_state)

    request_context = checkpoint.state_json.get("request_context")
    request_context_dict = cast(dict[str, object], request_context) if isinstance(request_context, dict) else {}
    user_input_value = request_context_dict.get("user_input")
    user_input = cast(dict[str, Any], user_input_value) if isinstance(user_input_value, dict) else {}
    merged_user_input = _apply_resume_patch_fields(user_input, payload.patch_fields)
    req = _user_input_to_request(merged_user_input)
    return await _process_lifecycle(db, payload.run_id, req, ai_state, lifecycle, settings)


async def get_order_status(
    db: Session,
    symbol: str,
    order_id: int | None,
    orig_client_order_id: str | None,
    settings: Settings,
) -> OrderStatusResponse:
    params: dict[str, Any] = {"symbol": symbol}
    if order_id is not None:
        params["orderId"] = order_id
    else:
        params["origClientOrderId"] = orig_client_order_id

    signed = build_signed_params(settings.binance_testnet_secret_key, params)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.binance_testnet_rest_base_url}/v3/order",
                headers={"X-MBX-APIKEY": settings.binance_testnet_api_key},
                params=signed,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Binance order status error: status=%s body=%s", e.response.status_code, e.response.text)
        raise
    except Exception:
        logger.exception("Unexpected error during Binance order status call")
        raise

    # 내부 DB에 해당 주문이 있을 때만 status log 저장
    binance_order_id = str(data.get("orderId", ""))
    existing = get_spot_order_by_binance_id(db, binance_order_id)
    if existing:
        save_order_status_log(db, order_id=existing.order_id, status_json=data)

    return OrderStatusResponse(
        order_id=data["orderId"],
        symbol=data["symbol"],
        status=data["status"],
        executed_qty=data["executedQty"],
    )


async def cancel_order(
    db: Session,
    req: CancelOrderRequest,
    settings: Settings,
) -> CancelOrderResponse:
    params: dict[str, Any] = {"symbol": req.symbol}
    if req.order_id is not None:
        params["orderId"] = req.order_id
    else:
        params["origClientOrderId"] = req.orig_client_order_id

    signed = build_signed_params(settings.binance_testnet_secret_key, params)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{settings.binance_testnet_rest_base_url}/v3/order",
                headers={"X-MBX-APIKEY": settings.binance_testnet_api_key},
                params=signed,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Binance cancel order error: status=%s body=%s", e.response.status_code, e.response.text)
        raise
    except Exception:
        logger.exception("Unexpected error during Binance cancel order call")
        raise

    binance_order_id = str(data.get("orderId", ""))
    existing = get_spot_order_by_binance_id(db, binance_order_id)
    if existing:
        update_spot_order_status(db, order_id=existing.order_id, status="CANCELED", response_json=data)
        order_pk = existing.order_id
    else:
        order_row = save_spot_order(
            db,
            symbol=req.symbol,
            request_json=req.model_dump(),
            binance_order_id=binance_order_id,
            status="CANCELED",
        )
        order_pk = order_row.order_id

    save_cancel_log(db, order_id=order_pk, cancel_json=data)
    return CancelOrderResponse(
        order_id=data["orderId"],
        symbol=data["symbol"],
        status=data["status"],
    )
