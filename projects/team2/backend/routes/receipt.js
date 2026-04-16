const express = require("express");
const router = express.Router();

router.post("/scan", async (req, res) => {
  const { image_url } = req.body;

  const response = await fetch(
    "https://api.upstage.ai/v1/document-ai/ocr",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.UPSTAGE_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ image_url }),
    }
  );

  const data = await response.json();
  res.json({ text: data.text, items: parseReceipt(data.text) });
});

function parseReceipt(text) {
  const lines = text.split("\n");
  return lines
    .filter((line) => /\d+원/.test(line))
    .map((line) => ({
      item: line.replace(/[\d,]+원.*/, "").trim(),
      price: parseInt(line.match(/[\d,]+/)?.[0]?.replace(",", "") || "0"),
    }));
}

module.exports = router;
