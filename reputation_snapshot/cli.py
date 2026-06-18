import click
from datetime import datetime, timedelta
from typing import List

from .analyzer import ReputationAnalyzer
from .batch_scanner import BatchScanner
from .storage import SnapshotStorage
from .formatter import OutputFormatter
from .models import Artist, RiskLevel


class Context:
    def __init__(self):
        self.analyzer = ReputationAnalyzer()
        self.batch_scanner = BatchScanner()
        self.storage = SnapshotStorage()
        self.formatter = OutputFormatter()


pass_ctx = click.make_pass_decorator(Context, ensure=True)


@click.group()
@click.version_option(version="1.0.0", prog_name="reputation-snapshot")
@pass_ctx
def cli(ctx):
    """口碑快照工具 - 舆情分析师专用命令行工具

    适用于深夜值班或批量监控时快速生成明星艺人口碑云图摘要。
    """
    pass


@cli.command()
@click.argument("artist_name")
@click.option(
    "-p", "--platform",
    type=click.Choice(["all", "weibo", "douyin", "xhs", "zhihu", "douban"]),
    default="all",
    help="监控平台范围，默认全平台",
)
@click.option(
    "-s", "--start-time",
    type=str,
    default=None,
    help="开始时间，格式：YYYY-MM-DD HH:MM，默认24小时前",
)
@click.option(
    "-e", "--end-time",
    type=str,
    default=None,
    help="结束时间，格式：YYYY-MM-DD HH:MM，默认当前时间",
)
@click.option(
    "-k", "--keyword",
    multiple=True,
    help="关注关键词，可多次指定",
)
@click.option(
    "--save",
    type=str,
    default=None,
    help="分析完成后保存快照，指定快照名称",
)
@click.option(
    "--notes",
    type=str,
    default="",
    help="快照备注信息",
)
@pass_ctx
def analyze(
    ctx: Context,
    artist_name: str,
    platform: str,
    start_time: str,
    end_time: str,
    keyword: List[str],
    save: str,
    notes: str,
):
    """分析单个艺人的舆情口碑快照

    ARTIST_NAME: 艺人名称
    """
    try:
        start_dt = _parse_datetime(start_time) if start_time else None
        end_dt = _parse_datetime(end_time) if end_time else None

        result = ctx.analyzer.analyze(
            artist_name=artist_name,
            platform=platform,
            start_time=start_dt,
            end_time=end_dt,
            focus_keywords=list(keyword),
        )

        ctx.formatter.print_analysis_result(result)

        if save:
            snapshot = ctx.storage.save(save, result, notes)
            ctx.formatter.print_success(f"快照已保存，ID: {snapshot.id}，名称: {snapshot.name}")

    except Exception as e:
        ctx.formatter.print_error(f"分析失败: {str(e)}")
        raise click.Abort()


@cli.command()
@click.option(
    "-f", "--file",
    type=str,
    required=True,
    help="艺人名单文件路径，每行一个艺人，格式：名称,别名1,别名2,优先级",
)
@click.option(
    "-p", "--platform",
    type=click.Choice(["all", "weibo", "douyin", "xhs", "zhihu", "douban"]),
    default="all",
    help="监控平台范围，默认全平台",
)
@click.option(
    "-s", "--start-time",
    type=str,
    default=None,
    help="开始时间，格式：YYYY-MM-DD HH:MM，默认24小时前",
)
@click.option(
    "-e", "--end-time",
    type=str,
    default=None,
    help="结束时间，格式：YYYY-MM-DD HH:MM，默认当前时间",
)
@click.option(
    "-k", "--keyword",
    multiple=True,
    help="关注关键词，可多次指定",
)
@click.option(
    "--min-risk",
    type=click.Choice(["low", "medium", "high", "critical"]),
    default=None,
    help="仅显示指定风险等级及以上的结果",
)
@click.option(
    "--night-report",
    is_flag=True,
    help="夜间值班报告模式，输出总览结论和优先级建议",
)
@click.option(
    "--compare-last",
    is_flag=True,
    help="与上次巡检对比，显示风险升降和异常词变化",
)
@pass_ctx
def batch(
    ctx: Context,
    file: str,
    platform: str,
    start_time: str,
    end_time: str,
    keyword: List[str],
    min_risk: str,
    night_report: bool,
    compare_last: bool,
):
    """批量扫描多位艺人并按风险等级排序"""
    try:
        artists = ctx.batch_scanner.load_artists_from_file(file)
        if not artists:
            ctx.formatter.print_error("艺人名单为空")
            raise click.Abort()

        start_dt = _parse_datetime(start_time) if start_time else None
        end_dt = _parse_datetime(end_time) if end_time else None

        results = ctx.batch_scanner.scan(
            artists=artists,
            platform=platform,
            start_time=start_dt,
            end_time=end_dt,
            focus_keywords=list(keyword),
        )

        if min_risk:
            risk_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            min_level = risk_order[min_risk]
            results = [
                r for r in results
                if risk_order[r.risk_level.value] >= min_level
            ]

        summary = ctx.batch_scanner.get_risk_summary(results)
        ctx.formatter.print_batch_results(results, summary, night_report=night_report)

        if compare_last:
            artist_names = [a.name for a in artists]
            comparison = ctx.storage.get_batch_comparison(artist_names)
            ctx.formatter.print_batch_comparison(comparison)

    except FileNotFoundError as e:
        ctx.formatter.print_error(str(e))
        raise click.Abort()
    except Exception as e:
        ctx.formatter.print_error(f"批量扫描失败: {str(e)}")
        raise click.Abort()


@cli.command(name="list")
@click.option(
    "-a", "--artist",
    type=str,
    default=None,
    help="仅显示指定艺人的快照",
)
@click.option(
    "-r", "--risk",
    type=click.Choice(["low", "medium", "high", "critical"]),
    default=None,
    help="仅显示指定风险等级的快照",
)
@click.option(
    "--start-time",
    type=str,
    default=None,
    help="仅显示此时间之后创建的快照，格式：YYYY-MM-DD HH:MM",
)
@click.option(
    "--end-time",
    type=str,
    default=None,
    help="仅显示此时间之前创建的快照，格式：YYYY-MM-DD HH:MM",
)
@click.option(
    "--export-md",
    type=str,
    default=None,
    help="导出为Markdown报告，指定输出文件路径",
)
@click.option(
    "--export-json",
    type=str,
    default=None,
    help="导出为JSON报告，指定输出文件路径",
)
@click.option(
    "--title",
    type=str,
    default="舆情快照报告",
    help="导出报告的标题",
)
@pass_ctx
def list_snapshots(
    ctx: Context,
    artist: str,
    risk: str,
    start_time: str,
    end_time: str,
    export_md: str,
    export_json: str,
    title: str,
):
    """列出所有本地快照，支持筛选和导出"""
    try:
        start_dt = _parse_datetime(start_time) if start_time else None
        end_dt = _parse_datetime(end_time) if end_time else None

        snapshots = ctx.storage.list(
            artist_name=artist,
            risk_level=risk,
            start_time=start_dt,
            end_time=end_dt,
        )
        ctx.formatter.print_snapshot_list(snapshots)

        filter_conditions = {}
        if artist:
            filter_conditions["artist"] = artist
        if risk:
            filter_conditions["risk_level"] = risk
        if start_time:
            filter_conditions["start_time"] = start_time
        if end_time:
            filter_conditions["end_time"] = end_time

        trend_summary = None
        follow_up_suggestions = None

        if export_md or export_json:
            artist_names = list(set(s["artist_name"] for s in snapshots))
            if artist_names:
                comparison = ctx.storage.get_batch_comparison(artist_names)
                trend_summary = {
                    "risk_escalated": comparison.get("risk_escalated", []),
                    "risk_decreased": comparison.get("risk_decreased", []),
                    "new_anomalies": comparison.get("new_anomalies", {}),
                    "resolved_anomalies": comparison.get("resolved_anomalies", {}),
                }

                follow_up_suggestions = {}
                for name in artist_names:
                    history = ctx.storage.get_artist_history(name, limit=1)
                    if history:
                        latest = history[0]
                        risk_level = RiskLevel(latest["risk_level"])
                        if latest.get("has_emergency"):
                            follow_up_suggestions[name] = "存在紧急预警词，需立即启动应急预案并持续监控"
                        elif risk_level == RiskLevel.CRITICAL:
                            follow_up_suggestions[name] = "极高风险，安排专人持续监控"
                        elif risk_level == RiskLevel.HIGH:
                            follow_up_suggestions[name] = "高风险，每2小时复查一次"
                        elif latest.get("anomaly_words"):
                            follow_up_suggestions[name] = "存在异常词，下次巡检时重点关注"
                        else:
                            follow_up_suggestions[name] = "态势平稳，正常频率巡检"

        if export_md:
            path = ctx.storage.export_markdown(
                snapshots, export_md, title,
                filter_conditions=filter_conditions,
                trend_summary=trend_summary,
                follow_up_suggestions=follow_up_suggestions,
            )
            ctx.formatter.print_success(f"Markdown报告已导出: {path}")

        if export_json:
            path = ctx.storage.export_json(
                snapshots, export_json,
                filter_conditions=filter_conditions,
                trend_summary=trend_summary,
                follow_up_suggestions=follow_up_suggestions,
            )
            ctx.formatter.print_success(f"JSON报告已导出: {path}")

    except Exception as e:
        ctx.formatter.print_error(f"获取快照列表失败: {str(e)}")
        raise click.Abort()


@cli.command()
@click.argument("artist_name")
@click.option(
    "-n", "--limit",
    type=int,
    default=10,
    help="显示最近N次快照，默认10",
)
@pass_ctx
def history(ctx: Context, artist_name: str, limit: int):
    """查看艺人的快照趋势视图

    ARTIST_NAME: 艺人名称
    """
    try:
        snapshots = ctx.storage.get_artist_history(artist_name, limit=limit)
        ctx.formatter.print_artist_history(artist_name, snapshots)
    except Exception as e:
        ctx.formatter.print_error(f"获取趋势数据失败: {str(e)}")
        raise click.Abort()


@cli.command()
@click.argument("snapshot_id")
@pass_ctx
def show(ctx: Context, snapshot_id: str):
    """查看指定快照的详细分析结果

    SNAPSHOT_ID: 快照ID
    """
    try:
        snapshot = ctx.storage.load(snapshot_id)
        if not snapshot:
            ctx.formatter.print_error(f"快照不存在: {snapshot_id}")
            raise click.Abort()

        ctx.formatter.print_analysis_result(snapshot.analysis_result)
    except Exception as e:
        ctx.formatter.print_error(f"查看快照失败: {str(e)}")
        raise click.Abort()


@cli.command()
@click.argument("snapshot_id")
@click.option(
    "--name",
    type=str,
    help="重命名快照",
)
@click.option(
    "--notes",
    type=str,
    help="修改备注",
)
@pass_ctx
def update(ctx: Context, snapshot_id: str, name: str, notes: str):
    """更新快照的名称或备注"""
    try:
        snapshot = ctx.storage.load(snapshot_id)
        if not snapshot:
            ctx.formatter.print_error(f"快照不存在: {snapshot_id}")
            raise click.Abort()

        if name:
            snapshot.name = name
        if notes is not None:
            snapshot.notes = notes

        file_path = ctx.storage._get_snapshot_path(snapshot_id)
        data = ctx.storage._snapshot_to_dict(snapshot)
        import json
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        ctx.formatter.print_success(f"快照已更新: {snapshot_id}")
    except Exception as e:
        ctx.formatter.print_error(f"更新快照失败: {str(e)}")
        raise click.Abort()


@cli.command()
@click.argument("snapshot_id")
@click.option(
    "--yes",
    is_flag=True,
    help="跳过确认直接删除",
)
@pass_ctx
def delete(ctx: Context, snapshot_id: str, yes: bool):
    """删除指定快照

    SNAPSHOT_ID: 快照ID
    """
    try:
        snapshot = ctx.storage.load(snapshot_id)
        if not snapshot:
            ctx.formatter.print_error(f"快照不存在: {snapshot_id}")
            raise click.Abort()

        if not yes:
            click.confirm(
                f"确定要删除快照 '{snapshot.name}' ({snapshot.artist_name}) 吗？",
                abort=True,
            )

        ctx.storage.delete(snapshot_id)
        ctx.formatter.print_success(f"快照已删除: {snapshot_id}")
    except click.Abort:
        raise
    except Exception as e:
        ctx.formatter.print_error(f"删除快照失败: {str(e)}")
        raise click.Abort()


@cli.command()
@click.argument("snapshot_id1")
@click.argument("snapshot_id2")
@pass_ctx
def compare(ctx: Context, snapshot_id1: str, snapshot_id2: str):
    """对比两个快照的差异

    SNAPSHOT_ID1: 第一个快照ID
    SNAPSHOT_ID2: 第二个快照ID
    """
    try:
        result = ctx.storage.compare(snapshot_id1, snapshot_id2)
        ctx.formatter.print_compare_result(result)
    except Exception as e:
        ctx.formatter.print_error(f"对比快照失败: {str(e)}")
        raise click.Abort()


@cli.command()
@click.option(
    "-o", "--output",
    type=str,
    default="./backups",
    help="备份输出路径（目录或zip文件路径）",
)
@pass_ctx
def backup(ctx: Context, output: str):
    """备份所有快照数据到zip文件"""
    try:
        path = ctx.storage.backup(output)
        ctx.formatter.print_success(f"快照已备份至: {path}")
    except Exception as e:
        ctx.formatter.print_error(f"备份失败: {str(e)}")
        raise click.Abort()


@cli.command()
@click.argument("backup_path")
@click.option(
    "--merge",
    is_flag=True,
    help="合并模式：跳过已存在的快照，不覆盖",
)
@click.option(
    "--yes",
    is_flag=True,
    help="跳过确认直接恢复",
)
@pass_ctx
def restore(ctx: Context, backup_path: str, merge: bool, yes: bool):
    """从备份zip文件恢复快照数据

    BACKUP_PATH: 备份文件路径
    """
    try:
        if not yes:
            action = "合并" if merge else "覆盖恢复"
            click.confirm(
                f"确定要从 {backup_path} {action}快照数据吗？",
                abort=True,
            )

        result = ctx.storage.restore(backup_path, merge=merge)
        parts = []
        if result["restored"]:
            parts.append(f"新增 {result['restored']} 个快照")
        if result["skipped"]:
            parts.append(f"跳过 {result['skipped']} 个已存在快照")
        if result["overwritten"]:
            parts.append(f"覆盖 {result['overwritten']} 个快照")
        ctx.formatter.print_success("恢复完成: " + "，".join(parts))
    except click.Abort:
        raise
    except FileNotFoundError as e:
        ctx.formatter.print_error(str(e))
        raise click.Abort()
    except Exception as e:
        ctx.formatter.print_error(f"恢复失败: {str(e)}")
        raise click.Abort()


@cli.command()
@click.option(
    "--before",
    type=str,
    required=True,
    help="归档此时间之前的快照，格式：YYYY-MM-DD",
)
@click.option(
    "--archive-dir",
    type=str,
    default=None,
    help="归档目录，默认为 snapshots/archive",
)
@click.option(
    "--yes",
    is_flag=True,
    help="跳过确认直接归档",
)
@pass_ctx
def archive(ctx: Context, before: str, archive_dir: str, yes: bool):
    """归档指定时间之前的快照（移动到归档目录，不删除）"""
    try:
        before_dt = _parse_datetime(before)

        if not yes:
            click.confirm(
                f"确定要归档 {before} 之前的快照吗？数据将移动到归档目录而非删除。",
                abort=True,
            )

        result = ctx.storage.archive_before(before_dt, archive_dir)
        ctx.formatter.print_success(
            f"归档完成: 归档 {result['archived']} 个快照，剩余 {result['remaining']} 个"
        )
        if result["archived_ids"]:
            ctx.formatter.print_warning(
                f"已归档快照ID: {', '.join(result['archived_ids'][:10])}"
                + ("..." if len(result["archived_ids"]) > 10 else "")
            )
    except click.Abort:
        raise
    except Exception as e:
        ctx.formatter.print_error(f"归档失败: {str(e)}")
        raise click.Abort()


@cli.command()
@click.option(
    "-p", "--path",
    type=str,
    default="./data/artists_example.txt",
    help="生成示例艺人名单文件的路径",
)
@pass_ctx
def init(ctx: Context, path: str):
    """生成示例艺人名单文件"""
    try:
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)

        example_content = """# 艺人名单示例文件
# 格式：艺人名称,别名1,别名2,优先级（1-5，数字越大优先级越高）
# 以#开头的行为注释

王一博,一博,耶啵,5
肖战,小战,战战,5
易烊千玺,千玺,四字,5
王俊凯,小凯,凯凯,4
王源,源源,4
张艺兴,艺兴,LAY,4
蔡徐坤,坤坤,4
华晨宇,花花,4
李现,现现,3
邓伦,伦伦,3
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(example_content)

        ctx.formatter.print_success(f"示例名单已生成: {path}")
        ctx.formatter.print_warning("请根据实际需求修改名单文件")
    except Exception as e:
        ctx.formatter.print_error(f"生成示例文件失败: {str(e)}")
        raise click.Abort()


def _parse_datetime(dt_str: str) -> datetime:
    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析时间格式: {dt_str}，支持的格式: {', '.join(formats)}")


def main():
    cli()


if __name__ == "__main__":
    main()
