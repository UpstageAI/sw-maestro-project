import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'api/calendar_api.dart';
import 'api/health_api.dart';
import 'api/workouts_api.dart';
import 'cards/calendar_card.dart';
import 'cards/calendar_reload_notifier.dart';
import 'cards/fatigue_radar_card.dart';
import 'cards/health_card.dart';
import 'cards/workouts_card.dart';
import 'chat/chat_panel.dart';
import 'chat/proposal_notifier.dart';
import 'design/app_theme.dart';
import 'design/tokens/colors.dart';
import 'design/tokens/radius.dart';
import 'design/tokens/shadows.dart';
import 'design/tokens/spacing.dart';
import 'design/tokens/typography.dart';
import 'env.dart';
import 'models/muscle_fatigue_state.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting('ko_KR');

  if (Env.isConfigured) {
    await Supabase.initialize(
      url: Env.supabaseUrl,
      anonKey: Env.supabaseAnonKey,
    );
  }

  runApp(const ExercisePlanningApp());
}

class ExercisePlanningApp extends StatelessWidget {
  const ExercisePlanningApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI 운동 코치',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      home: const DashboardPage(),
    );
  }
}

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  late DateTime _weekStart;
  late _DashboardApis _apis;
  late SupabaseClient _client;
  // Single source of truth for the latest agent proposal. ChatController fans
  // proposals out into this notifier (see lib/chat/), and FatigueRadarCard
  // listens so the radar reflects the agent's projected timeline.
  final _proposalNotifier = ProposalNotifier();
  // Bumped by ProposalCard after inserting events from a proposal so the
  // calendar card refetches without a full page reload.
  final _calendarReload = CalendarReloadNotifier();

  @override
  void initState() {
    super.initState();
    _weekStart = _mondayOfThisWeek(DateTime.now());
    // Hydrate registered-event-id tracking from localStorage so a refined
    // proposal can replace (not stack) the previous registration even after
    // a page reload. Issue #31.
    unawaited(_proposalNotifier.restore());
    if (Env.isConfigured) {
      _client = Supabase.instance.client;
      _apis = _DashboardApis(
        calendar: CalendarApi(_client),
        health: HealthApi(_client),
        workouts: WorkoutsApi(_client),
      );
    }
  }

  @override
  void dispose() {
    _proposalNotifier.dispose();
    _calendarReload.dispose();
    super.dispose();
  }

  void _shiftWeek(int weeks) {
    setState(() {
      _weekStart = _weekStart.add(Duration(days: 7 * weeks));
    });
  }

  void _resetToThisWeek() {
    setState(() {
      _weekStart = _mondayOfThisWeek(DateTime.now());
    });
  }

  @override
  Widget build(BuildContext context) {
    if (!Env.isConfigured) {
      return const _ConfigMissingPage();
    }

    return Scaffold(
      body: DecoratedBox(
        decoration: const BoxDecoration(gradient: AppColors.pageGradient),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              return SingleChildScrollView(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.s7,
                  vertical: AppSpacing.s6,
                ).copyWith(top: AppSpacing.s5),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _DashboardHeader(
                      weekStart: _weekStart,
                      onPrevWeek: () => _shiftWeek(-1),
                      onNextWeek: () => _shiftWeek(1),
                      onToday: _resetToThisWeek,
                    ),
                    const SizedBox(height: AppSpacing.s6),
                    _DashboardBody(
                      apis: _apis,
                      weekStart: _weekStart,
                      proposalNotifier: _proposalNotifier,
                      calendarReload: _calendarReload,
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

class _DashboardApis {
  const _DashboardApis({
    required this.calendar,
    required this.health,
    required this.workouts,
  });

  final CalendarApi calendar;
  final HealthApi health;
  final WorkoutsApi workouts;
}

DateTime _mondayOfThisWeek(DateTime now) {
  final date = DateTime(now.year, now.month, now.day);
  return date.subtract(Duration(days: date.weekday - DateTime.monday));
}

class _DashboardHeader extends StatelessWidget {
  const _DashboardHeader({
    required this.weekStart,
    required this.onPrevWeek,
    required this.onNextWeek,
    required this.onToday,
  });

  final DateTime weekStart;
  final VoidCallback onPrevWeek;
  final VoidCallback onNextWeek;
  final VoidCallback onToday;

  @override
  Widget build(BuildContext context) {
    final thisWeekStart = _mondayOfThisWeek(DateTime.now());
    final isThisWeek = weekStart.year == thisWeekStart.year &&
        weekStart.month == thisWeekStart.month &&
        weekStart.day == thisWeekStart.day;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Container(
          padding: const EdgeInsets.all(AppSpacing.s3),
          decoration: BoxDecoration(
            color: AppColors.bgElevated1,
            borderRadius: BorderRadius.circular(AppRadius.md),
            border: Border.all(color: AppColors.borderSubtle),
          ),
          child: Icon(
            LucideIcons.bot,
            size: 22,
            color: AppColors.accentPrimary,
          ),
        ),
        const SizedBox(width: AppSpacing.s4),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('AI 운동 코치', style: AppTypography.display),
              const SizedBox(height: 2),
              Text(
                '캘린더, 컨디션, 운동 이력을 종합해 이번 주 맞춤 스케줄을 제안합니다.',
                style: AppTypography.body.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
        _GhostButton(
          icon: LucideIcons.chevronLeft,
          label: '지난주',
          onTap: onPrevWeek,
        ),
        const SizedBox(width: AppSpacing.s2),
        _GhostButton(
          icon: LucideIcons.calendarDays,
          label: '오늘',
          onTap: isThisWeek ? null : onToday,
          highlighted: isThisWeek,
        ),
        const SizedBox(width: AppSpacing.s2),
        _GhostButton(
          icon: LucideIcons.chevronRight,
          label: '다음주',
          onTap: onNextWeek,
        ),
      ],
    );
  }
}

class _GhostButton extends StatelessWidget {
  const _GhostButton({
    required this.icon,
    required this.label,
    this.onTap,
    this.highlighted = false,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onTap;
  final bool highlighted;

  @override
  Widget build(BuildContext context) {
    final isDisabled = onTap == null;
    final fg = highlighted
        ? AppColors.accentPrimary
        : (isDisabled ? AppColors.textTertiary : AppColors.textSecondary);
    final borderColor = highlighted
        ? AppColors.accentPrimary.withValues(alpha: 0.4)
        : AppColors.borderSubtle;
    final bg = highlighted
        ? AppColors.accentPrimary.withValues(alpha: 0.08)
        : Colors.transparent;

    return MouseRegion(
      cursor: isDisabled ? SystemMouseCursors.basic : SystemMouseCursors.click,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(AppRadius.md),
          child: Ink(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.s3,
              vertical: AppSpacing.s2,
            ),
            decoration: BoxDecoration(
              color: bg,
              borderRadius: BorderRadius.circular(AppRadius.md),
              border: Border.all(color: borderColor),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icon, size: 14, color: fg),
                const SizedBox(width: AppSpacing.s1),
                Text(
                  label,
                  style: AppTypography.caption.copyWith(color: fg),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _DashboardBody extends StatelessWidget {
  const _DashboardBody({
    required this.apis,
    required this.weekStart,
    required this.proposalNotifier,
    required this.calendarReload,
  });

  final _DashboardApis apis;
  final DateTime weekStart;
  final ProposalNotifier proposalNotifier;
  final CalendarReloadNotifier calendarReload;

  @override
  Widget build(BuildContext context) {
    // ChatPanel 내부 ListView(=viewport)는 intrinsic 높이를 산출하지 못해서
    // IntrinsicHeight + Row(stretch) 로 묶으면 transcript 가 길어지는 순간
    // RenderViewport assertion 으로 트리가 폭주한다. 대신 좌측 카드 더미를
    // 한 번 측정해 그 높이를 우측 ChatPanel 에 tight 로 강제한다 — 좌측은
    // intrinsic 으로 안전하게 측정 가능하고, 우측은 이미 정해진 높이만 받으므로
    // ListView 가 잘 동작한다.
    final left = _LeftColumn(
      apis: apis,
      weekStart: weekStart,
      proposalNotifier: proposalNotifier,
      calendarReload: calendarReload,
    );
    return LayoutBuilder(
      builder: (context, constraints) {
        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(flex: 7, child: left),
            const SizedBox(width: AppSpacing.s5),
            Expanded(
              flex: 5,
              // 좌측이 차지할 높이의 근사치 — 페이지 viewport 높이를 상한으로
              // 두면 짧은 좌측에서도 채팅이 너무 길어지지 않고, 긴 좌측에서는
              // 좌측이 자연스럽게 더 커진 만큼 채팅이 같이 자란다.
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  maxHeight: constraints.hasBoundedHeight
                      ? constraints.maxHeight
                      : MediaQuery.of(context).size.height,
                ),
                child: ChatPanel(
                  proposalNotifier: proposalNotifier,
                  calendarApi: apis.calendar,
                  calendarReload: calendarReload,
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _LeftColumn extends StatelessWidget {
  const _LeftColumn({
    required this.apis,
    required this.weekStart,
    required this.proposalNotifier,
    required this.calendarReload,
  });

  final _DashboardApis apis;
  final DateTime weekStart;
  final ProposalNotifier proposalNotifier;
  final CalendarReloadNotifier calendarReload;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        CalendarCard(
          api: apis.calendar,
          weekStart: weekStart,
          reloadNotifier: calendarReload,
        ),
        const SizedBox(height: AppSpacing.s5),
        IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(child: HealthCard(api: apis.health)),
              const SizedBox(width: AppSpacing.s5),
              Expanded(child: WorkoutsCard(api: apis.workouts)),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.s5),
        _LiveFatigueRadar(notifier: proposalNotifier),
      ],
    );
  }
}

/// Listens to [ProposalNotifier] and feeds the latest agent-proposed fatigue
/// state into [FatigueRadarCard]. Falls back to [MuscleFatigueState.demo]
/// before the first proposal arrives so the radar is never empty.
class _LiveFatigueRadar extends StatelessWidget {
  const _LiveFatigueRadar({required this.notifier});

  final ProposalNotifier notifier;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: notifier,
      builder: (context, _) {
        final timeline = notifier.latest?.fatigueTimeline;
        final state = (timeline != null && timeline.isNotEmpty)
            ? timeline.first
            : MuscleFatigueState.demo();
        return FatigueRadarCard(state: state);
      },
    );
  }
}

class _ConfigMissingPage extends StatelessWidget {
  const _ConfigMissingPage();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: DecoratedBox(
        decoration: const BoxDecoration(gradient: AppColors.pageGradient),
        child: Center(
          child: Container(
            constraints: const BoxConstraints(maxWidth: 520),
            margin: const EdgeInsets.all(AppSpacing.s5),
            padding: const EdgeInsets.all(AppSpacing.s6),
            decoration: BoxDecoration(
              color: AppColors.bgElevated1,
              borderRadius: BorderRadius.circular(AppRadius.xl),
              border: Border.all(color: AppColors.borderSubtle),
              boxShadow: AppShadows.card,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  LucideIcons.keyRound,
                  size: 28,
                  color: AppColors.accentPrimary,
                ),
                const SizedBox(height: AppSpacing.s3),
                Text(
                  'Supabase 키가 설정되지 않았습니다',
                  style: AppTypography.h2,
                ),
                const SizedBox(height: AppSpacing.s2),
                Text(
                  '아래 명령으로 실행하세요. URL/anon key는 팀 채널에서 확인.',
                  style: AppTypography.body.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: AppSpacing.s4),
                Container(
                  padding: const EdgeInsets.all(AppSpacing.s4),
                  decoration: BoxDecoration(
                    color: AppColors.bgElevated2,
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    border: Border.all(color: AppColors.borderSubtle),
                  ),
                  child: const SelectableText(
                    'flutter run -d chrome \\\n'
                    '  --dart-define=SUPABASE_URL=https://<project>.supabase.co \\\n'
                    '  --dart-define=SUPABASE_ANON_KEY=<anon-key>',
                    style: TextStyle(
                      fontFamily: 'monospace',
                      color: AppColors.textSecondary,
                      fontSize: 12,
                      height: 1.7,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
