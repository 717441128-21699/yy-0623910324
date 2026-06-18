from typing import List, Dict
from rich.console import Console
from rich.table import Table, Column
from rich.panel import Panel
from rich.text import Text
from rich import box

from .models import AnalysisResult, RiskLevel, Sentiment, BatchScanResult, FollowUpStatus
from .anomaly_detector import AnomalyDetector


STATUS_LABELS = {
    "pending": "待处理",
    "in_progress": "处理中",
    "resolved": "已解决",
    "closed": "已闭环",
}

STATUS_COLORS = {
    "pending": "bright_yellow",
    "in_progress": "bright_blue",
    "resolved": "bright_magenta",
    "closed": "dim",
}

PRIORITY_LABELS = {
    "low": "低",
    "medium": "中",
    "high": "高",
    "critical": "紧急",
}

PRIORITY_COLORS = {
    "low": "dim",
    "medium": "bright_yellow",
    "high": "bright_magenta",
    "critical": "blink bold bright_red",
}


RISK_COLORS = {
    RiskLevel.LOW: "green",
    RiskLevel.MEDIUM: "yellow",
    RiskLevel.HIGH: "magenta",
    RiskLevel.CRITICAL: "bright_red",
}

RISK_LABELS = {
    RiskLevel.LOW: "低风险",
    RiskLevel.MEDIUM: "中风险",
    RiskLevel.HIGH: "高风险",
    RiskLevel.CRITICAL: "极高风险",
}

SENTIMENT_COLORS = {
    Sentiment.POSITIVE: "bright_green",
    Sentiment.NEUTRAL: "bright_blue",
    Sentiment.NEGATIVE: "bright_red",
}

SENTIMENT_LABELS = {
    Sentiment.POSITIVE: "正面",
    Sentiment.NEUTRAL: "中性",
    Sentiment.NEGATIVE: "负面",
}

PLATFORM_LABELS = {
    "weibo": "微博",
    "douyin": "抖音",
    "xhs": "小红书",
    "zhihu": "知乎",
    "douban": "豆瓣",
    "all": "全平台",
}


class OutputFormatter:
    def __init__(self):
        self.console = Console()
        self.anomaly_detector = AnomalyDetector()

    def print_analysis_result(self, result: AnalysisResult):
        anomalies = self.anomaly_detector.detect_from_result(result)

        self._print_header(result)

        self.console.print()
        self._print_discussion_volume(result)

        self.console.print()
        self._print_sentiment(result)

        self.console.print()
        self._print_trending_words(result, anomalies)

        self.console.print()
        self._print_controversy_points(result)

        if anomalies:
            self.console.print()
            self._print_anomalies(anomalies)

        self.console.print()
        self._print_risk(result)

        self.console.print()
        self._print_summary_text(result, anomalies)

    def _print_header(self, result: AnalysisResult):
        platform = PLATFORM_LABELS.get(result.platform, result.platform)
        header_text = Text()
        header_text.append("【舆情口碑快照】", style="bold bright_cyan")
        header_text.append(f" 艺人: ", style="dim")
        header_text.append(result.artist_name, style="bold bright_white")
        header_text.append(f" | 平台: ", style="dim")
        header_text.append(platform, style="bright_yellow")
        header_text.append(f" | 时间范围: ", style="dim")
        header_text.append(
            f"{result.start_time.strftime('%Y-%m-%d %H:%M')} ~ {result.end_time.strftime('%Y-%m-%d %H:%M')}",
            style="bright_blue"
        )
        if result.focus_keywords:
            header_text.append(f" | 关键词: ", style="dim")
            header_text.append(",".join(result.focus_keywords), style="bright_magenta")

        self.console.print(Panel(header_text, border_style="bright_cyan", box=box.DOUBLE))

    def _print_discussion_volume(self, result: AnalysisResult):
        table = Table(show_header=False, box=box.SIMPLE, expand=True)
        table.add_column("指标", style="dim", width=12)
        table.add_column("数值", style="bold")
        table.add_column("变化", width=15)

        volume_text = Text(f"{result.discussion_volume:,}")
        volume_text.stylize("bright_white")

        change_text = Text()
        if result.volume_change >= 0:
            change_text.append(f"+{result.volume_change:.1f}%", style="bright_green")
        else:
            change_text.append(f"{result.volume_change:.1f}%", style="bright_red")
        change_text.append(" 较昨日", style="dim")

        table.add_row("讨论总量", volume_text, change_text)

        self.console.print(
            Panel(table, title="📊 讨论量统计", title_align="left", border_style="bright_blue")
        )

    def _print_sentiment(self, result: AnalysisResult):
        sentiment_label = SENTIMENT_LABELS[result.sentiment]
        sentiment_color = SENTIMENT_COLORS[result.sentiment]

        score_bar_length = 20
        score = (result.sentiment_score + 1) / 2
        filled = int(score * score_bar_length)
        bar = "█" * filled + "░" * (score_bar_length - filled)

        bar_text = Text()
        if result.sentiment == Sentiment.POSITIVE:
            bar_text.append(bar, style="bright_green")
        elif result.sentiment == Sentiment.NEGATIVE:
            bar_text.append(bar, style="bright_red")
        else:
            bar_text.append(bar, style="bright_blue")

        table = Table(show_header=False, box=box.SIMPLE, expand=True)
        table.add_column("指标", style="dim", width=12)
        table.add_column("数值")

        table.add_row(
            "情绪倾向",
            Text(sentiment_label, style=f"bold {sentiment_color}")
        )
        table.add_row(
            "情绪指数",
            Text(f"{result.sentiment_score:+.2f} ", style=sentiment_color) + bar_text
        )

        self.console.print(
            Panel(table, title="🎭 情绪分析", title_align="left", border_style=sentiment_color)
        )

    def _print_trending_words(self, result: AnalysisResult, anomalies: List[Dict]):
        anomaly_words = {a["word"]: a for a in anomalies}

        table = Table(
            Column("评价词", style="bold", width=14),
            Column("提及数", justify="right", width=10),
            Column("增长率", justify="right", width=12),
            Column("热度", justify="center", width=20),
            Column("状态", width=12),
            box=box.SIMPLE,
            expand=True,
        )

        for word in result.top_trending_words[:8]:
            word_info = anomaly_words.get(word.word, {})
            is_emergency = word_info.get("is_emergency", False)
            is_spike = word_info.get("is_spike", False)

            word_text = Text(word.word)
            if is_emergency:
                word_text.stylize("blink bold bright_red on bright_yellow")
            elif is_spike:
                word_text.stylize("blink bold bright_red")

            count_text = Text(f"{word.count:,}", style="bright_white")

            growth_text = Text()
            if word.growth_rate >= 0:
                if is_emergency:
                    growth_text.append(f"+{word.growth_rate:.1f}%", style="blink bold bright_red")
                elif is_spike:
                    growth_text.append(f"+{word.growth_rate:.1f}%", style="bold bright_red")
                else:
                    growth_text.append(f"+{word.growth_rate:.1f}%", style="bright_green")
            else:
                growth_text.append(f"{word.growth_rate:.1f}%", style="bright_red")

            heat_level = min(5, max(1, int(word.count / 1000) + 1))
            heat_bar = "🔥" * heat_level

            status_text = Text()
            if is_emergency:
                status_text.append("🚨紧急", style="blink bold bright_red on bright_yellow")
            elif is_spike:
                status_text.append("⚠️飙升", style="blink bold bright_red")
            elif word.is_anomaly:
                status_text.append("异常", style="bold bright_red")
            elif word.growth_rate > 100:
                status_text.append("暴涨", style="bold bright_yellow")
            elif word.growth_rate > 50:
                status_text.append("飙升", style="bold bright_yellow")
            elif word.growth_rate > 0:
                status_text.append("上升", style="bright_green")
            else:
                status_text.append("平稳", style="dim")

            table.add_row(word_text, count_text, growth_text, heat_bar, status_text)

        self.console.print(
            Panel(table, title="🔥 上升最快评价词", title_align="left", border_style="bright_yellow")
        )

    def _print_controversy_points(self, result: AnalysisResult):
        table = Table(
            Column("争议点", style="bold", min_width=20, max_width=25),
            Column("提及数", justify="right", width=10),
            Column("传播风险", justify="center", width=12),
            Column("描述", overflow="fold", min_width=30),
            box=box.SIMPLE,
            expand=False,
        )

        if result.controversy_points:
            for point in result.controversy_points:
                keyword_text = Text(point.keyword, style="bright_red")
                mentions_text = Text(f"{point.mentions:,}", style="bright_white")

                spread_bar_length = 10
                filled = int(point.spread_potential * spread_bar_length)
                bar = "█" * filled + "░" * (spread_bar_length - filled)
                spread_text = Text(bar, style="bright_magenta")
                spread_text.append(f" {point.spread_potential:.0%}", style="dim")

                desc_text = Text(point.description, style="dim")

                table.add_row(keyword_text, mentions_text, spread_text, desc_text)
        else:
            table.add_row(
                Text("无明显扩散争议", style="bright_green"),
                Text("-", style="dim"),
                Text("-", style="dim"),
                Text("当前监测周期内未发现可能引发大规模扩散的争议性内容，口碑态势平稳", style="dim"),
            )

        self.console.print(
            Panel(table, title="⚠️  可能引发扩散的争议点", title_align="left", border_style="bright_magenta")
        )

    def _print_anomalies(self, anomalies: List[Dict]):
        table = Table(
            Column("异常词", style="bold", width=14),
            Column("类别", style="bold", width=12),
            Column("严重度", justify="center", width=10),
            Column("提及数", justify="right", width=10),
            Column("增长率", justify="right", width=12),
            Column("预警级别", width=12),
            Column("类型", width=10),
            box=box.SIMPLE,
            expand=True,
        )

        for anomaly in anomalies:
            is_emergency = anomaly.get("is_emergency", False)
            is_spike = anomaly.get("is_spike", False)

            if is_emergency:
                word_text = Text(f"🚨 {anomaly['word']}", style="blink bold bright_red on bright_yellow")
            elif is_spike:
                word_text = Text(f"⚠️ {anomaly['word']}", style="blink bold bright_red")
            else:
                word_text = Text(anomaly["word"], style="bold bright_red")

            category_text = Text(anomaly["category"], style="bright_yellow")

            severity_bar = "⚠️" * min(5, anomaly["severity"] // 2)
            severity_text = Text(severity_bar, style="bright_red")

            count_text = Text(f"{anomaly['count']:,}", style="bright_white")

            if is_emergency or is_spike:
                growth_text = Text(f"+{anomaly['growth_rate']:.1f}%", style="blink bold bright_red")
            else:
                growth_text = Text(f"+{anomaly['growth_rate']:.1f}%", style="bright_red")

            alert_text = Text()
            if is_emergency:
                alert_text.append("紧急预警", style="blink bold bright_red on bright_yellow")
            elif anomaly["severity_level"] == "critical":
                alert_text.append("严重", style="blink bold bright_red")
            elif anomaly["severity_level"] == "high":
                alert_text.append("高危", style="bold bright_magenta")
            else:
                alert_text.append("关注", style="bold bright_yellow")

            type_text = Text()
            if is_emergency and is_spike:
                type_text.append("突发飙升", style="blink bold bright_red")
            elif is_emergency:
                type_text.append("紧急", style="bold bright_red")
            elif is_spike:
                type_text.append("飙升", style="bold bright_yellow")
            else:
                type_text.append("上升", style="bright_yellow")

            table.add_row(word_text, category_text, severity_text, count_text, growth_text, alert_text, type_text)

        alert_summary = self.anomaly_detector.get_anomaly_summary(anomalies)
        self.console.print(
            Panel(
                table,
                title=f"🚨 异常词提醒 - {alert_summary}",
                title_align="left",
                border_style="bright_red",
            )
        )

    def _print_summary_text(self, result: AnalysisResult, anomalies: List[Dict]):
        summary = []
        summary.append(f"【结构化摘要】{result.artist_name} 舆情口碑快照")
        summary.append(f"时间范围: {result.start_time.strftime('%Y-%m-%d %H:%M')} ~ {result.end_time.strftime('%Y-%m-%d %H:%M')}")
        summary.append(f"平台: {PLATFORM_LABELS.get(result.platform, result.platform)}")
        summary.append(f"")
        summary.append(f"📊 当前讨论量: {result.discussion_volume:,}（较昨日{'+' if result.volume_change >= 0 else ''}{result.volume_change:.1f}%）")
        summary.append(f"🎭 情绪倾向: {SENTIMENT_LABELS[result.sentiment]}（指数 {result.sentiment_score:+.2f}）")

        top_words = [w.word for w in result.top_trending_words[:3]]
        summary.append(f"🔥 上升最快评价词: {', '.join(top_words)}")

        if result.controversy_points:
            top_controversy = result.controversy_points[0]
            summary.append(f"⚠️  主要争议点: {top_controversy.keyword}（提及 {top_controversy.mentions:,}，传播风险 {top_controversy.spread_potential:.0%}）")
        else:
            summary.append(f"⚠️  争议点: 无明显扩散争议，口碑态势平稳")

        if anomalies:
            anomaly_words = [a["word"] for a in anomalies[:3]]
            summary.append(f"🚨 异常词提醒: {', '.join(anomaly_words)}")
        else:
            summary.append(f"🚨 异常词: 无异常词")

        summary.append(f"🎯 风险等级: {RISK_LABELS[result.risk_level]}（风险分 {result.risk_score:.1f}/100）")

        suggestion = self._get_suggestion(result, anomalies)
        summary.append(f"")
        summary.append(f"💡 值班建议: {suggestion}")

        summary_text = Text("\n".join(summary), style="bright_white")
        self.console.print(
            Panel(summary_text, title="📋 结构化摘要（可直接复制）", title_align="left", border_style="bright_cyan", box=box.DOUBLE)
        )

    def _get_suggestion(self, result: AnalysisResult, anomalies: List[Dict]) -> str:
        if self.anomaly_detector.has_emergency_anomaly(anomalies):
            return "立即启动应急预案，持续监控舆情走向，准备危机公关方案"
        elif result.risk_level == RiskLevel.CRITICAL:
            return "高度关注，安排专人持续监控，准备应对措施"
        elif result.risk_level == RiskLevel.HIGH:
            return "重点关注，每2小时复查一次，注意异常词变化"
        elif result.risk_level == RiskLevel.MEDIUM:
            return "保持关注，正常巡检频率，留意讨论量变化"
        elif anomalies:
            return "注意异常词动向，下次巡检时重点关注"
        else:
            return "口碑态势平稳，按正常频率巡检即可"

    def _print_risk(self, result: AnalysisResult):
        risk_label = RISK_LABELS[result.risk_level]
        risk_color = RISK_COLORS[result.risk_level]

        score_bar_length = 20
        filled = int(result.risk_score / 100 * score_bar_length)
        bar = "█" * filled + "░" * (score_bar_length - filled)

        bar_text = Text(bar, style=risk_color)

        table = Table(show_header=False, box=box.SIMPLE, expand=True)
        table.add_column("指标", style="dim", width=12)
        table.add_column("数值")

        table.add_row(
            "风险等级",
            Text(risk_label, style=f"bold {risk_color}")
        )
        table.add_row(
            "风险指数",
            Text(f"{result.risk_score:.1f}/100 ", style=risk_color) + bar_text
        )

        self.console.print(
            Panel(table, title="🎯 风险评估", title_align="left", border_style=risk_color)
        )

    def print_batch_results(self, results: List[BatchScanResult], summary: Dict, night_report: bool = False):
        anomalies_detector = AnomalyDetector()

        title = Text(f"批量扫描结果 - 共 {summary['total']} 位艺人")
        title.stylize("bold bright_cyan")

        if summary.get("has_emergency"):
            emergency_names = ",".join(summary["emergency_artists"])
            alert_text = Text(f" 🚨 发现 {len(summary['emergency_artists'])} 个紧急预警艺人: {emergency_names}")
            alert_text.stylize("blink bold bright_red on bright_yellow")
            title.append_text(alert_text)
        elif summary["has_critical"]:
            critical_names = ",".join(summary["critical_artists"])
            alert_text = Text(f" ⚠️  发现 {summary['critical']} 个极高风险艺人: {critical_names}")
            alert_text.stylize("blink bold bright_red")
            title.append_text(alert_text)

        self.console.print(Panel(title, border_style="bright_cyan", box=box.DOUBLE))

        if night_report:
            self.console.print()
            self._print_night_report_summary(results, summary, anomalies_detector)

        self.console.print()

        summary_table = Table(show_header=True, box=box.SIMPLE, expand=True)
        summary_table.add_column("风险等级", style="bold")
        summary_table.add_column("数量", justify="right")
        summary_table.add_column("艺人", overflow="fold")

        for level, label in [
            (RiskLevel.CRITICAL, RISK_LABELS[RiskLevel.CRITICAL]),
            (RiskLevel.HIGH, RISK_LABELS[RiskLevel.HIGH]),
            (RiskLevel.MEDIUM, RISK_LABELS[RiskLevel.MEDIUM]),
            (RiskLevel.LOW, RISK_LABELS[RiskLevel.LOW]),
        ]:
            count = summary.get(level.value, 0)
            names = [
                r.artist.name
                for r in results
                if r.risk_level == level
            ]
            names_str = ",".join(names) if names else "-"
            summary_table.add_row(
                Text(label, style=RISK_COLORS[level]),
                Text(str(count), style="bold bright_white"),
                Text(names_str, style=RISK_COLORS[level]),
            )

        self.console.print(
            Panel(summary_table, title="📋 风险分布", title_align="left", border_style="bright_blue")
        )

        self.console.print()

        detail_table = Table(
            Column("排名", justify="right", width=6),
            Column("优先级", justify="center", width=8),
            Column("艺人", style="bold", width=15),
            Column("风险等级", justify="center", width=10),
            Column("风险分", justify="right", width=8),
            Column("讨论量", justify="right", width=12),
            Column("情绪", justify="center", width=8),
            Column("异常词", width=24, overflow="fold"),
            Column("预警", width=10),
            box=box.SIMPLE,
            expand=True,
        )

        for idx, r in enumerate(results, 1):
            anomalies = anomalies_detector.detect_from_result(r.analysis_result)
            has_emergency = anomalies_detector.has_emergency_anomaly(anomalies)
            has_spike = anomalies_detector.has_spike_anomaly(anomalies)

            rank_text = Text(str(idx), style="dim")
            priority_text = Text("★" * r.artist.priority, style="bright_yellow")

            name_text = Text(r.artist.name)
            if has_emergency:
                name_text.stylize("blink bold bright_red on bright_yellow")
            elif has_spike:
                name_text.stylize("blink bold bright_red")

            risk_text = Text(RISK_LABELS[r.risk_level], style=RISK_COLORS[r.risk_level])
            score_text = Text(f"{r.risk_score:.1f}", style=RISK_COLORS[r.risk_level])
            volume_text = Text(f"{r.analysis_result.discussion_volume:,}", style="bright_white")
            sentiment_text = Text(
                SENTIMENT_LABELS[r.analysis_result.sentiment],
                style=SENTIMENT_COLORS[r.analysis_result.sentiment],
            )

            anomaly_parts = []
            for a in anomalies[:3]:
                if a.get("is_emergency"):
                    anomaly_parts.append(f"🚨{a['word']}")
                elif a.get("is_spike"):
                    anomaly_parts.append(f"⚠️{a['word']}")
                else:
                    anomaly_parts.append(a["word"])
            anomalies_str = ",".join(anomaly_parts) if anomaly_parts else "-"

            anomalies_text = Text(anomalies_str)
            if has_emergency:
                anomalies_text.stylize("blink bold bright_red on bright_yellow")
            elif has_spike:
                anomalies_text.stylize("blink bold bright_red")
            elif anomaly_parts:
                anomalies_text.stylize("bright_red")
            else:
                anomalies_text.stylize("dim")

            alert_text = Text()
            if has_emergency:
                alert_text.append("🚨紧急", style="blink bold bright_red on bright_yellow")
            elif has_spike:
                alert_text.append("⚠️飙升", style="blink bold bright_red")
            elif anomalies:
                alert_text.append("异常", style="bold bright_red")
            else:
                alert_text.append("-", style="dim")

            detail_table.add_row(
                rank_text,
                priority_text,
                name_text,
                risk_text,
                score_text,
                volume_text,
                sentiment_text,
                anomalies_text,
                alert_text,
            )

        self.console.print(
            Panel(detail_table, title="📊 详细排行（按风险等级降序）", title_align="left", border_style="bright_yellow")
        )

    def _print_night_report_summary(self, results: List[BatchScanResult], summary: Dict, detector: AnomalyDetector):
        top_3 = results[:3]
        anomaly_map = {}
        for r in results:
            anomalies = detector.detect_from_result(r.analysis_result)
            for a in anomalies:
                if a["word"] not in anomaly_map:
                    anomaly_map[a["word"]] = {"count": 0, "artists": [], "is_emergency": False, "is_spike": False}
                anomaly_map[a["word"]]["count"] += 1
                anomaly_map[a["word"]]["artists"].append(r.artist.name)
                if a.get("is_emergency"):
                    anomaly_map[a["word"]]["is_emergency"] = True
                if a.get("is_spike"):
                    anomaly_map[a["word"]]["is_spike"] = True

        report_lines = []
        report_lines.append("【🌙 夜间值班总览】")
        report_lines.append("")

        if top_3:
            report_lines.append("🎯 最高风险艺人 TOP3:")
            for i, r in enumerate(top_3, 1):
                anomalies = detector.detect_from_result(r.analysis_result)
                anomaly_str = ",".join([a["word"] for a in anomalies[:2]]) if anomalies else "无"
                report_lines.append(f"  {i}. {r.artist.name} - {RISK_LABELS[r.risk_level]}({r.risk_score:.1f}分) - 异常词: {anomaly_str}")
            report_lines.append("")

        if anomaly_map:
            report_lines.append("🚨 异常词集中分布:")
            sorted_anomalies = sorted(anomaly_map.items(), key=lambda x: (-x[1]["count"], -x[1].get("is_emergency", False)))
            for word, info in sorted_anomalies[:5]:
                tag = ""
                if info["is_emergency"]:
                    tag = " 🚨紧急"
                elif info["is_spike"]:
                    tag = " ⚠️飙升"
                artists_str = ",".join(info["artists"][:3])
                if len(info["artists"]) > 3:
                    artists_str += f" 等{len(info['artists'])}人"
                report_lines.append(f"  • {word}{tag} - 涉及 {info['count']} 人: {artists_str}")
            report_lines.append("")

        report_lines.append("💡 建议优先跟进:")
        priority_list = []
        for r in results:
            anomalies = detector.detect_from_result(r.analysis_result)
            if detector.has_emergency_anomaly(anomalies):
                priority_list.append((r.artist.name, "立即处理", "紧急预警"))
            elif r.risk_level == RiskLevel.CRITICAL:
                priority_list.append((r.artist.name, "立即跟进", "极高风险"))
            elif detector.has_spike_anomaly(anomalies):
                priority_list.append((r.artist.name, "重点关注", "异常飙升"))
            elif r.risk_level == RiskLevel.HIGH:
                priority_list.append((r.artist.name, "密切关注", "高风险"))

        if priority_list:
            for i, (name, action, reason) in enumerate(priority_list[:5], 1):
                report_lines.append(f"  {i}. {name} - {action}（{reason}）")
        else:
            report_lines.append("  所有艺人口碑态势平稳，按正常频率巡检即可")

        report_text = Text("\n".join(report_lines), style="bright_white")
        self.console.print(
            Panel(report_text, title="🌙 夜间值班报告", title_align="left", border_style="bright_magenta", box=box.DOUBLE)
        )

    def print_snapshot_list(self, snapshots: List[Dict]):
        if not snapshots:
            self.console.print(Panel("[dim]暂无快照记录[/dim]", border_style="dim"))
            return

        table = Table(
            Column("ID", style="bold bright_blue", width=10),
            Column("名称", style="bold", width=18),
            Column("艺人", width=12),
            Column("创建时间", width=20),
            Column("风险等级", justify="center", width=10),
            Column("风险分", justify="right", width=8),
            Column("讨论量", justify="right", width=12),
            Column("情绪", justify="center", width=8),
            Column("异常词", width=20, overflow="fold"),
            Column("预警", width=10),
            Column("备注", overflow="fold"),
            box=box.SIMPLE,
            expand=True,
        )

        for s in snapshots:
            risk_level = RiskLevel(s["risk_level"])
            sentiment = Sentiment(s["sentiment"])

            has_emergency = s.get("has_emergency", False)
            has_spike = s.get("has_spike", False)
            anomaly_words = s.get("anomaly_words", [])

            name_text = Text(s["name"])
            if has_emergency:
                name_text.stylize("blink bold bright_red on bright_yellow")
            elif has_spike:
                name_text.stylize("blink bold bright_red")

            anomaly_parts = []
            for w in anomaly_words[:3]:
                if w in self.anomaly_detector.emergency_words:
                    anomaly_parts.append(f"🚨{w}")
                elif has_spike:
                    anomaly_parts.append(f"⚠️{w}")
                else:
                    anomaly_parts.append(w)
            anomaly_str = ",".join(anomaly_parts) if anomaly_parts else "-"

            anomalies_text = Text(anomaly_str)
            if has_emergency:
                anomalies_text.stylize("blink bold bright_red on bright_yellow")
            elif has_spike:
                anomalies_text.stylize("blink bold bright_red")
            elif anomaly_parts:
                anomalies_text.stylize("bright_red")
            else:
                anomalies_text.stylize("dim")

            alert_text = Text()
            if has_emergency:
                alert_text.append("🚨紧急", style="blink bold bright_red on bright_yellow")
            elif has_spike:
                alert_text.append("⚠️飙升", style="blink bold bright_red")
            elif anomaly_words:
                alert_text.append("异常", style="bold bright_red")
            else:
                alert_text.append("-", style="dim")

            table.add_row(
                s["id"],
                name_text,
                s["artist_name"],
                s["created_at"],
                Text(RISK_LABELS[risk_level], style=RISK_COLORS[risk_level]),
                Text(f"{s['risk_score']:.1f}", style=RISK_COLORS[risk_level]),
                f"{s['discussion_volume']:,}",
                Text(SENTIMENT_LABELS[sentiment], style=SENTIMENT_COLORS[sentiment]),
                anomalies_text,
                alert_text,
                s.get("notes", ""),
            )

        self.console.print(
            Panel(table, title=f"💾 本地快照列表 (共 {len(snapshots)} 条)", title_align="left", border_style="bright_cyan")
        )

    def print_compare_result(self, compare_data: Dict):
        if "error" in compare_data:
            self.console.print(Panel(f"[bright_red]{compare_data['error']}[/bright_red]", border_style="bright_red"))
            return

        s1 = compare_data["snapshot1"]
        s2 = compare_data["snapshot2"]

        title = Text(
            f"快照对比 - {compare_data['artist_name']} | "
            f"{s1['name']} → {s2['name']} | "
            f"间隔 {compare_data['time_diff']:.1f} 小时"
        )
        title.stylize("bold bright_cyan")

        self.console.print(Panel(title, border_style="bright_cyan", box=box.DOUBLE))

        self.console.print()
        self._print_compare_metrics(compare_data)

        self.console.print()
        self._print_compare_words(compare_data)

        self.console.print()
        self._print_compare_anomalies(compare_data)

    def _print_compare_metrics(self, data: Dict):
        table = Table(
            Column("指标", style="dim", width=15),
            Column("旧值", justify="right"),
            Column("新值", justify="right"),
            Column("变化", justify="right"),
            box=box.SIMPLE,
            expand=True,
        )

        vol = data["volume_change"]
        vol_diff = Text()
        if vol["diff"] > 0:
            vol_diff.append(f"+{vol['diff']:,} (+{vol['percent']:.1f}%)", style="bright_green")
        else:
            vol_diff.append(f"{vol['diff']:,} ({vol['percent']:.1f}%)", style="bright_red")
        table.add_row("讨论量", f"{vol['old']:,}", f"{vol['new']:,}", vol_diff)

        sent = data["sentiment_change"]
        sent_old = Text(sent["old"], style=SENTIMENT_COLORS[Sentiment(sent["old"])])
        sent_new = Text(sent["new"], style=SENTIMENT_COLORS[Sentiment(sent["new"])])
        sent_diff = Text()
        if sent["diff"] > 0:
            sent_diff.append(f"+{sent['diff']:+.2f}", style="bright_green")
        else:
            sent_diff.append(f"{sent['diff']:+.2f}", style="bright_red")
        table.add_row("情绪", sent_old, sent_new, sent_diff)

        risk = data["risk_change"]
        risk_old = Text(risk["old"], style=RISK_COLORS[RiskLevel(risk["old"])])
        risk_new = Text(risk["new"], style=RISK_COLORS[RiskLevel(risk["new"])])
        risk_diff = Text()
        if risk["diff"] > 0:
            risk_diff.append(f"+{risk['diff']:+.1f}", style="bright_red")
        elif risk["diff"] < 0:
            risk_diff.append(f"{risk['diff']:+.1f}", style="bright_green")
        else:
            risk_diff.append(f"{risk['diff']:+.1f}", style="dim")
        table.add_row("风险等级", risk_old, risk_new, risk_diff)

        self.console.print(
            Panel(table, title="📈 指标变化", title_align="left", border_style="bright_blue")
        )

    def _print_compare_words(self, data: Dict):
        table = Table(
            Column("关键词", style="bold", width=14),
            Column("旧计数", justify="right", width=10),
            Column("新计数", justify="right", width=10),
            Column("热度变化", justify="right", width=12),
            Column("趋势", width=12),
            Column("预警", width=10),
            box=box.SIMPLE,
            expand=True,
        )

        detector = AnomalyDetector()
        for wc in data["word_changes"]:
            is_emergency = wc["word"] in detector.emergency_words
            is_spike = wc["growth_change"] > detector.spike_threshold

            word_text = Text(wc["word"])
            if is_emergency and wc["growth_change"] > 0:
                word_text.stylize("blink bold bright_red on bright_yellow")
            elif is_spike and wc["growth_change"] > 0:
                word_text.stylize("blink bold bright_red")

            trend_text = Text()
            if is_emergency and wc["growth_change"] > 0:
                trend_text.append("🚨紧急", style="blink bold bright_red on bright_yellow")
            elif is_spike and wc["growth_change"] > 0:
                trend_text.append("⚠️飙升", style="blink bold bright_red")
            elif wc["growth_change"] > 50:
                trend_text.append("暴涨", style="bold bright_yellow")
            elif wc["growth_change"] > 20:
                trend_text.append("飙升", style="bold bright_yellow")
            elif wc["growth_change"] > 0:
                trend_text.append("上升", style="bright_green")
            elif wc["growth_change"] < -50:
                trend_text.append("暴跌", style="bold bright_blue")
            elif wc["growth_change"] < -20:
                trend_text.append("骤降", style="bright_blue")
            elif wc["growth_change"] < 0:
                trend_text.append("下降", style="dim")
            else:
                trend_text.append("平稳", style="dim")

            growth_text = Text()
            if wc["growth_change"] > 0:
                if is_emergency:
                    growth_text.append(f"+{wc['growth_change']:.1f}%", style="blink bold bright_red")
                elif is_spike:
                    growth_text.append(f"+{wc['growth_change']:.1f}%", style="bold bright_red")
                else:
                    growth_text.append(f"+{wc['growth_change']:.1f}%", style="bright_green")
            else:
                growth_text.append(f"{wc['growth_change']:.1f}%", style="bright_red")

            alert_text = Text()
            if is_emergency and wc["growth_change"] > 0:
                alert_text.append("🚨紧急", style="blink bold bright_red on bright_yellow")
            elif is_spike and wc["growth_change"] > 0:
                alert_text.append("⚠️飙升", style="blink bold bright_red")
            elif wc["word"] in detector.critical_words and wc["growth_change"] > detector.growth_threshold:
                alert_text.append("异常", style="bold bright_red")
            else:
                alert_text.append("-", style="dim")

            table.add_row(
                word_text,
                f"{wc['count1']:,}",
                f"{wc['count2']:,}",
                growth_text,
                trend_text,
                alert_text,
            )

        self.console.print(
            Panel(table, title="🔥 热词变化TOP10", title_align="left", border_style="bright_yellow")
        )

    def _print_compare_anomalies(self, data: Dict):
        if not data["new_anomalies"] and not data["resolved_anomalies"]:
            self.console.print(Panel("[dim]无异常词变化[/dim]", border_style="dim"))
            return

        table = Table(
            Column("变化类型", style="bold", width=14),
            Column("异常词", style="bold", width=14),
            Column("预警级别", width=12),
            Column("备注", overflow="fold"),
            box=box.SIMPLE,
            expand=True,
        )

        detector = AnomalyDetector()
        for word in data["new_anomalies"]:
            is_emergency = word in detector.emergency_words
            if is_emergency:
                table.add_row(
                    Text("新增异常", style="blink bold bright_red on bright_yellow"),
                    Text(f"🚨 {word}", style="blink bold bright_red on bright_yellow"),
                    Text("紧急预警", style="blink bold bright_red on bright_yellow"),
                    Text("高危词突发，需立即关注", style="bright_red"),
                )
            else:
                table.add_row(
                    Text("新增异常", style="blink bold bright_red"),
                    Text(f"⚠️ {word}", style="blink bold bright_red"),
                    Text("飙升警告", style="blink bold bright_red"),
                    Text("风险词快速上升，需密切关注", style="bright_yellow"),
                )

        for word in data["resolved_anomalies"]:
            table.add_row(
                Text("已消除", style="bright_green"),
                Text(word, style="dim"),
                Text("风险解除", style="bright_green"),
                Text("异常词热度下降，恢复正常", style="dim"),
            )

        self.console.print(
            Panel(table, title="🚨 异常词变化", title_align="left", border_style="bright_red")
        )

    def print_success(self, message: str):
        self.console.print(Text(f"✓ {message}", style="bright_green"))

    def print_error(self, message: str):
        self.console.print(Text(f"✗ {message}", style="bright_red"))

    def print_warning(self, message: str):
        self.console.print(Text(f"⚠ {message}", style="bright_yellow"))

    def print_artist_history(self, artist_name: str, history: List[Dict]):
        if not history:
            self.console.print(Panel(
                f"[dim]艺人 {artist_name} 暂无快照记录，请先使用 analyze 命令分析并保存快照[/dim]",
                border_style="dim"
            ))
            return

        title = Text(f"📈 趋势视图 - {artist_name}（共 {len(history)} 次快照）")
        title.stylize("bold bright_cyan")
        self.console.print(Panel(title, border_style="bright_cyan", box=box.DOUBLE))

        self.console.print()
        self._print_history_trend_table(artist_name, history)

        self.console.print()
        self._print_history_trend_chart(history)

        self.console.print()
        self._print_history_anomaly_changes(history)

        self.console.print()
        self._print_history_conclusion(artist_name, history)

    def _print_history_trend_table(self, artist_name: str, history: List[Dict]):
        table = Table(
            Column("序号", justify="right", width=6),
            Column("快照名称", style="bold", width=18),
            Column("创建时间", width=20),
            Column("讨论量", justify="right", width=12),
            Column("风险分", justify="right", width=8),
            Column("风险等级", justify="center", width=10),
            Column("情绪", justify="center", width=8),
            Column("争议数", justify="right", width=8),
            Column("异常词", width=20, overflow="fold"),
            Column("趋势", width=8),
            box=box.SIMPLE,
            expand=True,
        )

        for idx, s in enumerate(history, 1):
            risk_level = RiskLevel(s["risk_level"])
            sentiment = Sentiment(s["sentiment"])

            trend_text = Text()
            if idx > 1:
                prev = history[idx - 2]
                risk_diff = s["risk_score"] - prev["risk_score"]
                vol_diff = s["discussion_volume"] - prev["discussion_volume"]
                if risk_diff > 10:
                    trend_text.append("🔥升温", style="blink bold bright_red")
                elif risk_diff > 0:
                    trend_text.append("↑微升", style="bright_red")
                elif risk_diff < -10:
                    trend_text.append("↓降温", style="bright_green")
                elif risk_diff < 0:
                    trend_text.append("↓微降", style="bright_green")
                else:
                    trend_text.append("→持平", style="dim")
            else:
                trend_text.append("-", style="dim")

            anomaly_words = s.get("anomaly_words", [])
            has_emergency = s.get("has_emergency", False)
            anomaly_parts = []
            for w in anomaly_words[:3]:
                if w in self.anomaly_detector.emergency_words:
                    anomaly_parts.append(f"🚨{w}")
                else:
                    anomaly_parts.append(w)
            anomaly_str = ",".join(anomaly_parts) if anomaly_parts else "-"
            anomalies_text = Text(anomaly_str)
            if has_emergency:
                anomalies_text.stylize("blink bold bright_red on bright_yellow")
            elif anomaly_parts:
                anomalies_text.stylize("bright_red")
            else:
                anomalies_text.stylize("dim")

            table.add_row(
                str(idx),
                s["name"],
                s["created_at"],
                f"{s['discussion_volume']:,}",
                Text(f"{s['risk_score']:.1f}", style=RISK_COLORS[risk_level]),
                Text(RISK_LABELS[risk_level], style=RISK_COLORS[risk_level]),
                Text(SENTIMENT_LABELS[sentiment], style=SENTIMENT_COLORS[sentiment]),
                str(s.get("controversy_count", 0)),
                anomalies_text,
                trend_text,
            )

        self.console.print(
            Panel(table, title="📊 历史快照序列", title_align="left", border_style="bright_blue")
        )

    def _print_history_trend_chart(self, history: List[Dict]):
        volumes = [s["discussion_volume"] for s in history]
        risks = [s["risk_score"] for s in history]
        max_vol = max(volumes) if volumes else 1
        min_vol = min(volumes) if volumes else 0
        chart_width = 30

        vol_bars = []
        risk_bars = []
        for v, r in zip(volumes, risks):
            if max_vol > min_vol:
                vol_filled = int((v - min_vol) / (max_vol - min_vol) * chart_width)
            else:
                vol_filled = chart_width // 2
            vol_bars.append("█" * max(1, vol_filled) + "░" * (chart_width - max(1, vol_filled)))
            risk_filled = int(r / 100 * chart_width)
            risk_bars.append("█" * max(1, risk_filled) + "░" * (chart_width - max(1, risk_filled)))

        vol_table = Table(
            Column("时间", width=16),
            Column("讨论量", justify="right", width=10),
            Column("趋势", width=chart_width + 2),
            Column("方向", width=6),
            box=box.SIMPLE,
            expand=True,
        )

        for i, s in enumerate(history):
            vol_bar = Text(vol_bars[i], style="bright_blue")
            dir_text = Text()
            if i > 0:
                diff = volumes[i] - volumes[i - 1]
                if diff > 0:
                    dir_text.append("↑", style="bright_red")
                elif diff < 0:
                    dir_text.append("↓", style="bright_green")
                else:
                    dir_text.append("→", style="dim")
            vol_table.add_row(
                s["created_at"][:16],
                f"{volumes[i]:,}",
                vol_bar,
                dir_text,
            )

        self.console.print(
            Panel(vol_table, title="📈 讨论量趋势", title_align="left", border_style="bright_blue")
        )

        self.console.print()

        risk_table = Table(
            Column("时间", width=16),
            Column("风险分", justify="right", width=10),
            Column("趋势", width=chart_width + 2),
            Column("方向", width=6),
            box=box.SIMPLE,
            expand=True,
        )

        for i, s in enumerate(history):
            risk_level = RiskLevel(s["risk_level"])
            risk_bar = Text(risk_bars[i], style=RISK_COLORS[risk_level])
            dir_text = Text()
            if i > 0:
                diff = risks[i] - risks[i - 1]
                if diff > 5:
                    dir_text.append("↑↑", style="blink bold bright_red")
                elif diff > 0:
                    dir_text.append("↑", style="bright_red")
                elif diff < -5:
                    dir_text.append("↓↓", style="bright_green")
                elif diff < 0:
                    dir_text.append("↓", style="bright_green")
                else:
                    dir_text.append("→", style="dim")
            risk_table.add_row(
                s["created_at"][:16],
                Text(f"{risks[i]:.1f}", style=RISK_COLORS[risk_level]),
                risk_bar,
                dir_text,
            )

        self.console.print(
            Panel(risk_table, title="🎯 风险分趋势", title_align="left", border_style="bright_magenta")
        )

    def _print_history_anomaly_changes(self, history: List[Dict]):
        if len(history) < 2:
            self.console.print(Panel("[dim]仅1次快照，暂无异常词变化记录[/dim]", border_style="dim"))
            return

        table = Table(
            Column("对比", width=25),
            Column("新增异常词", width=18),
            Column("消除异常词", width=18),
            Column("持续异常词", width=18),
            box=box.SIMPLE,
            expand=True,
        )

        for i in range(1, len(history)):
            prev_words = set(history[i - 1].get("anomaly_words", []))
            curr_words = set(history[i].get("anomaly_words", []))

            new_words = curr_words - prev_words
            resolved = prev_words - curr_words
            ongoing = curr_words & prev_words

            new_text = Text(",".join(sorted(new_words)) if new_words else "-",
                           style="blink bold bright_red" if new_words else "dim")
            resolved_text = Text(",".join(sorted(resolved)) if resolved else "-",
                                style="bright_green" if resolved else "dim")
            ongoing_text = Text(",".join(sorted(ongoing)) if ongoing else "-",
                               style="bright_yellow" if ongoing else "dim")

            label = f"{history[i-1]['name']} → {history[i]['name']}"
            table.add_row(label, new_text, resolved_text, ongoing_text)

        self.console.print(
            Panel(table, title="🚨 异常词逐次变化", title_align="left", border_style="bright_red")
        )

    def _print_history_conclusion(self, artist_name: str, history: List[Dict]):
        if len(history) < 2:
            conclusion = f"仅有1次快照，无法判断趋势，建议持续监控并保存更多快照"
            conclusion_text = Text(conclusion, style="bright_white")
            self.console.print(
                Panel(conclusion_text, title="📋 趋势结论", title_align="left", border_style="bright_cyan")
            )
            return

        latest = history[-1]
        earliest = history[0]
        risk_diff = latest["risk_score"] - earliest["risk_score"]
        vol_diff = latest["discussion_volume"] - earliest["discussion_volume"]

        lines = []
        lines.append(f"【{artist_name} 趋势结论】")
        lines.append("")

        if risk_diff > 20:
            lines.append(f"⚠️ 风险显著上升: 从 {earliest['risk_score']:.1f} 升至 {latest['risk_score']:.1f}（+{risk_diff:.1f}）")
        elif risk_diff > 0:
            lines.append(f"📈 风险微升: 从 {earliest['risk_score']:.1f} 升至 {latest['risk_score']:.1f}（+{risk_diff:.1f}）")
        elif risk_diff < -20:
            lines.append(f"✅ 风险显著下降: 从 {earliest['risk_score']:.1f} 降至 {latest['risk_score']:.1f}（{risk_diff:.1f}）")
        elif risk_diff < 0:
            lines.append(f"📉 风险微降: 从 {earliest['risk_score']:.1f} 降至 {latest['risk_score']:.1f}（{risk_diff:.1f}）")
        else:
            lines.append(f"➡️ 风险持平: 维持在 {latest['risk_score']:.1f}")

        if vol_diff > 0:
            lines.append(f"📊 讨论量上升: 从 {earliest['discussion_volume']:,} 升至 {latest['discussion_volume']:,}（+{vol_diff:,}）")
        elif vol_diff < 0:
            lines.append(f"📊 讨论量下降: 从 {earliest['discussion_volume']:,} 降至 {latest['discussion_volume']:,}（{vol_diff:,}）")
        else:
            lines.append(f"📊 讨论量持平: 维持在 {latest['discussion_volume']:,}")

        all_anomalies = set()
        for s in history:
            for w in s.get("anomaly_words", []):
                all_anomalies.add(w)
        if all_anomalies:
            lines.append(f"🚨 历史异常词: {', '.join(sorted(all_anomalies))}")
        else:
            lines.append(f"🚨 历史异常词: 无")

        latest_anomaly = latest.get("anomaly_words", [])
        if latest.get("has_emergency"):
            lines.append(f"💡 建议: 当前存在紧急预警词，需立即启动应急预案")
        elif risk_diff > 20:
            lines.append(f"💡 建议: 风险上升趋势明显，加密巡检频率至每2小时一次")
        elif risk_diff > 0:
            lines.append(f"💡 建议: 风险有所上升，保持关注，下次巡检时重点复查")
        elif risk_diff < -20:
            lines.append(f"💡 建议: 风险明显回落，可恢复正常巡检频率")
        else:
            lines.append(f"💡 建议: 态势平稳，按正常频率巡检")

        conclusion_text = Text("\n".join(lines), style="bright_white")
        self.console.print(
            Panel(conclusion_text, title="📋 趋势结论", title_align="left", border_style="bright_cyan", box=box.DOUBLE)
        )

    def print_batch_comparison(self, comparison: Dict):
        if not comparison.get("has_previous"):
            self.console.print(Panel(
                "[dim]未找到历史快照，无法生成对比结论。本次为首次巡检。[/dim]",
                border_style="dim"
            ))
            return

        title = Text(f"📊 与上次巡检对比（{comparison['compared_count']}/{comparison['total_count']} 人可对比）")
        title.stylize("bold bright_cyan")
        self.console.print(Panel(title, border_style="bright_cyan", box=box.DOUBLE))

        self.console.print()

        if comparison.get("risk_escalated"):
            table = Table(
                Column("艺人", style="bold", width=15),
                Column("旧风险", justify="center", width=12),
                Column("新风险", justify="center", width=12),
                Column("风险分变化", justify="right", width=12),
                Column("趋势", width=8),
                box=box.SIMPLE,
                expand=True,
            )
            for item in comparison["risk_escalated"]:
                old_level = RiskLevel(item["old_level"])
                new_level = RiskLevel(item["new_level"])
                diff = item["new_score"] - item["old_score"]
                table.add_row(
                    Text(item["name"], style="blink bold bright_red"),
                    Text(RISK_LABELS[old_level], style=RISK_COLORS[old_level]),
                    Text(RISK_LABELS[new_level], style=RISK_COLORS[new_level]),
                    Text(f"+{diff:.1f}", style="blink bold bright_red"),
                    Text("🔥升温", style="blink bold bright_red"),
                )
            self.console.print(
                Panel(table, title="⚠️ 风险新升高", title_align="left", border_style="bright_red")
            )
            self.console.print()

        if comparison.get("risk_decreased"):
            table = Table(
                Column("艺人", style="bold", width=15),
                Column("旧风险", justify="center", width=12),
                Column("新风险", justify="center", width=12),
                Column("风险分变化", justify="right", width=12),
                Column("趋势", width=8),
                box=box.SIMPLE,
                expand=True,
            )
            for item in comparison["risk_decreased"]:
                old_level = RiskLevel(item["old_level"])
                new_level = RiskLevel(item["new_level"])
                diff = item["new_score"] - item["old_score"]
                table.add_row(
                    item["name"],
                    Text(RISK_LABELS[old_level], style=RISK_COLORS[old_level]),
                    Text(RISK_LABELS[new_level], style=RISK_COLORS[new_level]),
                    Text(f"{diff:.1f}", style="bright_green"),
                    Text("✅降温", style="bright_green"),
                )
            self.console.print(
                Panel(table, title="✅ 风险已回落", title_align="left", border_style="bright_green")
            )
            self.console.print()

        if comparison.get("new_anomalies"):
            table = Table(
                Column("艺人", style="bold", width=15),
                Column("新增异常词", style="bold"),
                box=box.SIMPLE,
                expand=True,
            )
            for artist, words in comparison["new_anomalies"].items():
                word_str = ",".join(words)
                is_emergency = any(w in self.anomaly_detector.emergency_words for w in words)
                if is_emergency:
                    table.add_row(
                        Text(artist, style="blink bold bright_red on bright_yellow"),
                        Text(f"🚨 {word_str}", style="blink bold bright_red on bright_yellow"),
                    )
                else:
                    table.add_row(
                        Text(artist, style="bold bright_red"),
                        Text(f"⚠️ {word_str}", style="bold bright_red"),
                    )
            self.console.print(
                Panel(table, title="🚨 新增异常词", title_align="left", border_style="bright_red")
            )
            self.console.print()

        if comparison.get("resolved_anomalies"):
            table = Table(
                Column("艺人", style="bold", width=15),
                Column("消除异常词", style="bold"),
                box=box.SIMPLE,
                expand=True,
            )
            for artist, words in comparison["resolved_anomalies"].items():
                table.add_row(
                    Text(artist, style="bright_green"),
                    Text(",".join(words), style="dim"),
                )
            self.console.print(
                Panel(table, title="✅ 异常词已回落", title_align="left", border_style="bright_green")
            )
            self.console.print()

        if not comparison.get("risk_escalated") and not comparison.get("new_anomalies"):
            self.console.print(Panel(
                "[bright_green]本次巡检与上次相比无风险升高和新增异常词，态势平稳[/bright_green]",
                border_style="bright_green"
            ))

    def print_followup_list(self, items: List[Dict]):
        if not items:
            self.console.print(Panel("[dim]暂无跟进事项[/dim]", border_style="dim"))
            return

        table = Table(
            Column("ID", width=10),
            Column("艺人", width=12),
            Column("标题", width=25),
            Column("优先级", width=8, justify="center"),
            Column("状态", width=10, justify="center"),
            Column("负责人", width=10),
            Column("下次复查", width=18),
            Column("创建时间", width=18),
            Column("备注", width=25),
            box=box.SIMPLE,
            expand=True,
        )

        for item in items:
            priority = item["priority"]
            status = item["status"]
            priority_text = Text(PRIORITY_LABELS.get(priority, priority),
                                style=PRIORITY_COLORS.get(priority, "dim"))
            status_text = Text(STATUS_LABELS.get(status, status),
                              style=STATUS_COLORS.get(status, "dim"))
            next_review = item.get("next_review_time")
            if next_review:
                next_review = next_review[:16].replace("T", " ")
            else:
                next_review = "-"
            created_at = item["created_at"][:16].replace("T", " ")
            notes = item.get("notes", "")[:20] + ("..." if len(item.get("notes", "")) > 20 else "")
            table.add_row(
                item["id"],
                item["artist_name"],
                item["title"],
                priority_text,
                status_text,
                item.get("assignee", "-") or "-",
                next_review,
                created_at,
                notes or "-",
            )

        open_count = len([i for i in items if i["status"] in ["pending", "in_progress", "resolved"]])
        title = f"📋 跟进台账（共 {len(items)} 条，未闭环 {open_count} 条）"
        self.console.print(Panel(table, title=title, title_align="left", border_style="bright_blue"))

    def print_window_stats(self, artist_name: str, stats: Dict):
        WINDOW_LABELS = {"24h": "24小时", "7d": "7天", "30d": "30天"}
        TREND_LABELS = {
            "rising": ("🔥 持续升温", "bright_red"),
            "falling": ("✅ 持续降温", "bright_green"),
            "stable": ("→ 波动平稳", "bright_yellow"),
            "insufficient_data": ("- 数据不足", "dim"),
        }

        table = Table(
            Column("时间窗口", width=12, justify="center"),
            Column("快照数", width=8, justify="center"),
            Column("风险峰值", width=12, justify="center"),
            Column("讨论量峰值", width=12, justify="right"),
            Column("高频异常词", width=25),
            Column("趋势判断", width=14, justify="center"),
            box=box.SIMPLE,
            expand=True,
        )

        for window in ["24h", "7d", "30d"]:
            data = stats[window]
            if data["snapshot_count"] == 0:
                table.add_row(
                    WINDOW_LABELS[window],
                    Text("0", style="dim"),
                    Text("-", style="dim"),
                    Text("-", style="dim"),
                    Text("-", style="dim"),
                    Text("-", style="dim"),
                )
                continue

            risk_level = data["peak_risk_level"]
            risk_color = RISK_COLORS.get(RiskLevel(risk_level), "dim")
            risk_text = Text(f"{data['peak_risk_score']:.0f}", style=risk_color)

            volume_text = Text(f"{data['peak_discussion_volume']:,}", style="bright_cyan")

            anomaly_parts = []
            for word, count in data["anomaly_word_counts"].items():
                style = "blink bold bright_red" if count >= 3 else "bright_red"
                anomaly_parts.append(Text(f"{word}×{count}", style=style))
            anomaly_text = Text(" ")
            for i, part in enumerate(anomaly_parts):
                if i > 0:
                    anomaly_text.append(", ")
                anomaly_text.append(part)
            if not anomaly_parts:
                anomaly_text = Text("-", style="dim")

            trend_label, trend_color = TREND_LABELS.get(data["trend"], ("-", "dim"))
            trend_text = Text(trend_label, style=trend_color)

            table.add_row(
                WINDOW_LABELS[window],
                str(data["snapshot_count"]),
                risk_text,
                volume_text,
                anomaly_text,
                trend_text,
            )

        self.console.print(
            Panel(table, title=f"⏱️ 时间窗口汇总 - {artist_name}", title_align="left", border_style="bright_cyan")
        )
        self.console.print()

    def print_archive_preview(self, result: Dict):
        if result["archived"] == 0:
            self.console.print(Panel(
                "[dim]没有需要归档的快照[/dim]",
                title="⚠️ 归档预览",
                title_align="left",
                border_style="bright_yellow"
            ))
            return

        table = Table(
            Column("ID", width=12),
            Column("名称", width=20),
            Column("艺人", width=12),
            Column("风险等级", width=10, justify="center"),
            Column("创建时间", width=20),
            box=box.SIMPLE,
            expand=True,
        )

        for detail in result["archived_details"]:
            risk_level = detail["risk_level"]
            risk_color = RISK_COLORS.get(RiskLevel(risk_level), "dim")
            risk_text = Text(RISK_LABELS.get(RiskLevel(risk_level), risk_level),
                              style=risk_color)
            created_at = detail["created_at"][:16].replace("T", " ")
            table.add_row(
                detail["id"],
                detail["name"],
                detail["artist_name"],
                risk_text,
                created_at,
            )

        title = f"📦 归档预览（共 {result['archived']} 个快照）"
        self.console.print(Panel(table, title=title, title_align="left", border_style="bright_yellow"))

        info_lines = []
        info_lines.append(f"涉及艺人: {', '.join(result['artist_names'][:5])}")
        if len(result['artist_names']) > 5:
            info_lines[-1] += f" 等 {len(result['artist_names'])} 人"
        if result['time_range']['earliest'] and result['time_range']['latest']:
            earliest = result['time_range']['earliest'][:16].replace("T", " ")
            latest = result['time_range']['latest'][:16].replace("T", " ")
            info_lines.append(f"时间范围: {earliest} ~ {latest}")
        info_lines.append(f"归档目录: {result['archive_dir']}")
        info_lines.append(f"归档后剩余: {result['remaining']} 个快照")

        info_text = Text("\n").join([Text(line, style="dim") for line in info_lines])
        self.console.print(Panel(info_text, border_style="dim"))

    def print_auto_add_preview(self, result: Dict):
        created = result["created"]
        skipped = result["skipped"]
        total = len(created) + len(skipped)

        if total == 0:
            self.console.print(Panel(
                "[dim]无可生成的跟进事项（指定艺人无历史快照或全部已存在同类未闭环事项）[/dim]",
                title="📋 自动生成跟进事项预览",
                title_align="left",
                border_style="dim"
            ))
            return

        if created:
            table = Table(
                Column("ID", width=10),
                Column("艺人", width=12),
                Column("分类", width=14, justify="center"),
                Column("生成原因", width=50),
                box=box.SIMPLE,
                expand=True,
            )
            category_labels = {
                "emergency": ("🚨 紧急预警", "blink bold bright_red"),
                "critical": ("🔴 极高风险", "bright_red"),
                "high": ("🟠 高风险", "bright_magenta"),
                "recurrent": ("🔁 反复异常", "bright_yellow"),
                "anomaly": ("⚠️ 异常词", "yellow"),
            }
            for item in created:
                label, color = category_labels.get(item["category"], (item["category"], "dim"))
                table.add_row(
                    item["id"],
                    item["artist"],
                    Text(label, style=color),
                    item["reason"],
                )
            self.console.print(
                Panel(table, title=f"✅ 拟创建（{len(created)} 项）", title_align="left", border_style="bright_green")
            )

        if skipped:
            skip_table = Table(
                Column("艺人", width=12),
                Column("分类", width=14, justify="center"),
                Column("跳过原因", width=40),
                box=box.SIMPLE,
                expand=True,
            )
            for item in skipped:
                skip_table.add_row(
                    item["artist"],
                    item["category"],
                    item["reason"],
                )
            self.console.print(
                Panel(skip_table, title=f"⏭️  已跳过（{len(skipped)} 项，去重）", title_align="left", border_style="dim")
            )

