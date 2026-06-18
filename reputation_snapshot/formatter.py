from typing import List, Dict
from rich.console import Console
from rich.table import Table, Column
from rich.panel import Panel
from rich.text import Text
from rich import box

from .models import AnalysisResult, RiskLevel, Sentiment, BatchScanResult
from .anomaly_detector import AnomalyDetector


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
