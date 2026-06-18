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

        title = Text(f"舆情口碑快照 - {result.artist_name}")
        title.stylize("bold bright_cyan")

        self._print_header(result)

        self.console.print()
        self._print_discussion_volume(result)

        self.console.print()
        self._print_sentiment(result)

        self.console.print()
        self._print_trending_words(result, anomalies)

        if result.controversy_points:
            self.console.print()
            self._print_controversy_points(result)

        if anomalies:
            self.console.print()
            self._print_anomalies(anomalies)

        self.console.print()
        self._print_risk(result)

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
            Column("评价词", style="bold", width=12),
            Column("提及数", justify="right", width=10),
            Column("增长率", justify="right", width=12),
            Column("热度", justify="center", width=20),
            Column("状态", width=10),
            box=box.SIMPLE,
            expand=True,
        )

        for word in result.top_trending_words[:8]:
            word_text = Text(word.word)
            if word.word in anomaly_words:
                word_text.stylize("blink bold bright_red")

            count_text = Text(f"{word.count:,}", style="bright_white")

            growth_text = Text()
            if word.growth_rate >= 0:
                growth_text.append(f"+{word.growth_rate:.1f}%", style="bright_green")
            else:
                growth_text.append(f"{word.growth_rate:.1f}%", style="bright_red")

            heat_level = min(5, max(1, int(word.count / 1000) + 1))
            heat_bar = "🔥" * heat_level

            status_text = Text()
            if word.is_anomaly:
                status_text.append("异常", style="blink bold bright_red")
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

        self.console.print(
            Panel(table, title="⚠️  可能引发扩散的争议点", title_align="left", border_style="bright_magenta")
        )

    def _print_anomalies(self, anomalies: List[Dict]):
        table = Table(
            Column("异常词", style="bold", width=12),
            Column("类别", style="bold", width=12),
            Column("严重度", justify="center", width=10),
            Column("提及数", justify="right", width=10),
            Column("增长率", justify="right", width=12),
            Column("预警", width=10),
            box=box.SIMPLE,
            expand=True,
        )

        for anomaly in anomalies:
            word_text = Text(anomaly["word"], style="blink bold bright_red")
            category_text = Text(anomaly["category"], style="bright_yellow")

            severity_bar = "⚠️" * min(5, anomaly["severity"] // 2)
            severity_text = Text(severity_bar, style="bright_red")

            count_text = Text(f"{anomaly['count']:,}", style="bright_white")

            growth_text = Text(f"+{anomaly['growth_rate']:.1f}%", style="blink bright_red")

            alert_text = Text()
            if anomaly["severity_level"] == "critical":
                alert_text.append("严重", style="blink bold bright_red")
            elif anomaly["severity_level"] == "high":
                alert_text.append("高危", style="bold bright_magenta")
            else:
                alert_text.append("关注", style="bold bright_yellow")

            table.add_row(word_text, category_text, severity_text, count_text, growth_text, alert_text)

        alert_summary = self.anomaly_detector.get_anomaly_summary(anomalies)
        self.console.print(
            Panel(
                table,
                title=f"🚨 异常词提醒 - {alert_summary}",
                title_align="left",
                border_style="bright_red",
            )
        )

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

    def print_batch_results(self, results: List[BatchScanResult], summary: Dict):
        title = Text(f"批量扫描结果 - 共 {summary['total']} 位艺人")
        title.stylize("bold bright_cyan")

        if summary["has_critical"]:
            critical_names = ",".join(summary["critical_artists"])
            alert_text = Text(f" ⚠️  发现 {summary['critical']} 个极高风险艺人: {critical_names}")
            alert_text.stylize("blink bold bright_red")
            title.append_text(alert_text)

        self.console.print(Panel(title, border_style="bright_cyan", box=box.DOUBLE))

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
            Column("异常词", width=20, overflow="fold"),
            box=box.SIMPLE,
            expand=True,
        )

        for idx, r in enumerate(results, 1):
            rank_text = Text(str(idx), style="dim")
            priority_text = Text("★" * r.artist.priority, style="bright_yellow")
            name_text = Text(r.artist.name)
            risk_text = Text(RISK_LABELS[r.risk_level], style=RISK_COLORS[r.risk_level])
            score_text = Text(f"{r.risk_score:.1f}", style=RISK_COLORS[r.risk_level])
            volume_text = Text(f"{r.analysis_result.discussion_volume:,}", style="bright_white")
            sentiment_text = Text(
                SENTIMENT_LABELS[r.analysis_result.sentiment],
                style=SENTIMENT_COLORS[r.analysis_result.sentiment],
            )
            anomalies_str = ",".join(r.analysis_result.anomaly_words) if r.analysis_result.anomaly_words else "-"
            anomalies_text = Text(anomalies_str, style="bright_red" if r.analysis_result.anomaly_words else "dim")

            detail_table.add_row(
                rank_text,
                priority_text,
                name_text,
                risk_text,
                score_text,
                volume_text,
                sentiment_text,
                anomalies_text,
            )

        self.console.print(
            Panel(detail_table, title="📊 详细排行（按风险等级降序）", title_align="left", border_style="bright_yellow")
        )

    def print_snapshot_list(self, snapshots: List[Dict]):
        if not snapshots:
            self.console.print(Panel("[dim]暂无快照记录[/dim]", border_style="dim"))
            return

        table = Table(
            Column("ID", style="bold bright_blue", width=10),
            Column("名称", style="bold", width=20),
            Column("艺人", width=15),
            Column("创建时间", width=20),
            Column("风险等级", justify="center", width=10),
            Column("风险分", justify="right", width=8),
            Column("讨论量", justify="right", width=12),
            Column("情绪", justify="center", width=8),
            Column("备注", overflow="fold"),
            box=box.SIMPLE,
            expand=True,
        )

        for s in snapshots:
            risk_level = RiskLevel(s["risk_level"])
            sentiment = Sentiment(s["sentiment"])

            table.add_row(
                s["id"],
                s["name"],
                s["artist_name"],
                s["created_at"],
                Text(RISK_LABELS[risk_level], style=RISK_COLORS[risk_level]),
                Text(f"{s['risk_score']:.1f}", style=RISK_COLORS[risk_level]),
                f"{s['discussion_volume']:,}",
                Text(SENTIMENT_LABELS[sentiment], style=SENTIMENT_COLORS[sentiment]),
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
            Column("关键词", style="bold", width=12),
            Column("旧计数", justify="right", width=10),
            Column("新计数", justify="right", width=10),
            Column("热度变化", justify="right", width=12),
            Column("趋势", width=8),
            box=box.SIMPLE,
            expand=True,
        )

        for wc in data["word_changes"]:
            trend_text = Text()
            if wc["growth_change"] > 20:
                trend_text.append("飙升", style="blink bold bright_red")
            elif wc["growth_change"] > 0:
                trend_text.append("上升", style="bright_green")
            elif wc["growth_change"] < -20:
                trend_text.append("骤降", style="bright_blue")
            elif wc["growth_change"] < 0:
                trend_text.append("下降", style="dim")
            else:
                trend_text.append("平稳", style="dim")

            growth_text = Text()
            if wc["growth_change"] > 0:
                growth_text.append(f"+{wc['growth_change']:.1f}%", style="bright_green")
            else:
                growth_text.append(f"{wc['growth_change']:.1f}%", style="bright_red")

            table.add_row(
                wc["word"],
                f"{wc['count1']:,}",
                f"{wc['count2']:,}",
                growth_text,
                trend_text,
            )

        self.console.print(
            Panel(table, title="🔥 热词变化TOP10", title_align="left", border_style="bright_yellow")
        )

    def _print_compare_anomalies(self, data: Dict):
        if not data["new_anomalies"] and not data["resolved_anomalies"]:
            self.console.print(Panel("[dim]无异常词变化[/dim]", border_style="dim"))
            return

        table = Table(
            Column("变化类型", style="bold", width=12),
            Column("异常词", style="bold"),
            box=box.SIMPLE,
            expand=True,
        )

        for word in data["new_anomalies"]:
            table.add_row(
                Text("新增异常", style="blink bold bright_red"),
                Text(word, style="blink bold bright_red"),
            )

        for word in data["resolved_anomalies"]:
            table.add_row(
                Text("已消除", style="bright_green"),
                Text(word, style="dim"),
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
