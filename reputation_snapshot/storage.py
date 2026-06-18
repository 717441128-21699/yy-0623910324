import json
import os
import uuid
import shutil
import zipfile
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from pathlib import Path

from .models import Snapshot, AnalysisResult, Sentiment, RiskLevel, TrendingWord, ControversyPoint
from .anomaly_detector import AnomalyDetector


RISK_LABEL_MAP = {"critical": "极高风险", "high": "高风险", "medium": "中风险", "low": "低风险"}
SENTIMENT_LABEL_MAP = {"positive": "正面", "neutral": "中性", "negative": "负面"}


class SnapshotStorage:
    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            storage_dir = os.path.join(os.getcwd(), "snapshots")
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.anomaly_detector = AnomalyDetector()

    def save(
        self,
        name: str,
        analysis_result: AnalysisResult,
        notes: str = "",
    ) -> Snapshot:
        snapshot_id = str(uuid.uuid4())[:8]
        snapshot = Snapshot(
            id=snapshot_id,
            name=name,
            artist_name=analysis_result.artist_name,
            analysis_result=analysis_result,
            created_at=datetime.now(),
            notes=notes,
        )

        file_path = self._get_snapshot_path(snapshot_id)
        data = self._snapshot_to_dict(snapshot)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        return snapshot

    def load(self, snapshot_id: str) -> Optional[Snapshot]:
        file_path = self._get_snapshot_path(snapshot_id)
        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return self._dict_to_snapshot(data)

    def list(
        self,
        artist_name: str = None,
        risk_level: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
    ) -> List[Dict]:
        snapshots = []
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if artist_name and data["artist_name"] != artist_name:
                    continue

                if risk_level and data["analysis_result"]["risk_level"] != risk_level:
                    continue

                created_at = datetime.fromisoformat(data["created_at"])
                if start_time and created_at < start_time:
                    continue
                if end_time and created_at > end_time:
                    continue

                result_data = data["analysis_result"]
                anomalies = self.anomaly_detector.detect([
                    TrendingWord(**w) for w in result_data["top_trending_words"]
                ])
                has_emergency = any(a.get("is_emergency") for a in anomalies)
                has_spike = any(a.get("is_spike") for a in anomalies)
                anomaly_words = [a["word"] for a in anomalies]

                snapshots.append({
                    "id": data["id"],
                    "name": data["name"],
                    "artist_name": data["artist_name"],
                    "created_at": data["created_at"],
                    "risk_level": result_data["risk_level"],
                    "risk_score": result_data["risk_score"],
                    "sentiment": result_data["sentiment"],
                    "sentiment_score": result_data.get("sentiment_score", 0),
                    "discussion_volume": result_data["discussion_volume"],
                    "anomaly_words": anomaly_words,
                    "has_emergency": has_emergency,
                    "has_spike": has_spike,
                    "notes": data.get("notes", ""),
                })
            except (json.JSONDecodeError, KeyError):
                continue

        return sorted(snapshots, key=lambda x: x["created_at"], reverse=True)

    def get_artist_history(self, artist_name: str, limit: int = 10) -> List[Dict]:
        snapshots = []
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data["artist_name"] != artist_name:
                    continue
                result_data = data["analysis_result"]
                anomalies = self.anomaly_detector.detect([
                    TrendingWord(**w) for w in result_data["top_trending_words"]
                ])
                snapshots.append({
                    "id": data["id"],
                    "name": data["name"],
                    "artist_name": data["artist_name"],
                    "created_at": data["created_at"],
                    "risk_level": result_data["risk_level"],
                    "risk_score": result_data["risk_score"],
                    "sentiment": result_data["sentiment"],
                    "sentiment_score": result_data.get("sentiment_score", 0),
                    "discussion_volume": result_data["discussion_volume"],
                    "volume_change": result_data["volume_change"],
                    "anomaly_words": [a["word"] for a in anomalies],
                    "has_emergency": any(a.get("is_emergency") for a in anomalies),
                    "has_spike": any(a.get("is_spike") for a in anomalies),
                    "controversy_count": len(result_data.get("controversy_points", [])),
                    "top_words": [w["word"] for w in result_data["top_trending_words"][:3]],
                    "notes": data.get("notes", ""),
                })
            except (json.JSONDecodeError, KeyError):
                continue

        snapshots.sort(key=lambda x: x["created_at"])
        return snapshots[-limit:] if limit else snapshots

    def get_batch_comparison(self, artist_names: List[str]) -> Dict:
        current_map = {}
        previous_map = {}
        for name in artist_names:
            history = self.get_artist_history(name, limit=2)
            if len(history) >= 1:
                current_map[name] = history[-1]
            if len(history) >= 2:
                previous_map[name] = history[-2]

        risk_escalated = []
        risk_decreased = []
        new_anomalies_map = {}
        resolved_anomalies_map = {}

        risk_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}

        for name in artist_names:
            curr = current_map.get(name)
            prev = previous_map.get(name)
            if not curr or not prev:
                continue

            curr_rank = risk_order.get(curr["risk_level"], 0)
            prev_rank = risk_order.get(prev["risk_level"], 0)

            if curr_rank > prev_rank:
                risk_escalated.append({
                    "name": name,
                    "old_level": prev["risk_level"],
                    "new_level": curr["risk_level"],
                    "old_score": prev["risk_score"],
                    "new_score": curr["risk_score"],
                })
            elif curr_rank < prev_rank:
                risk_decreased.append({
                    "name": name,
                    "old_level": prev["risk_level"],
                    "new_level": curr["risk_level"],
                    "old_score": prev["risk_score"],
                    "new_score": curr["risk_score"],
                })

            prev_anomalies = set(prev.get("anomaly_words", []))
            curr_anomalies = set(curr.get("anomaly_words", []))
            new_a = curr_anomalies - prev_anomalies
            resolved_a = prev_anomalies - curr_anomalies
            if new_a:
                new_anomalies_map[name] = list(new_a)
            if resolved_a:
                resolved_anomalies_map[name] = list(resolved_a)

        return {
            "has_previous": len(previous_map) > 0,
            "compared_count": len(previous_map),
            "total_count": len(artist_names),
            "risk_escalated": risk_escalated,
            "risk_decreased": risk_decreased,
            "new_anomalies": new_anomalies_map,
            "resolved_anomalies": resolved_anomalies_map,
        }

    def backup(self, output_path: str) -> str:
        output_path = Path(output_path)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_path.suffix != ".zip":
            output_path = output_path / f"snapshot_backup_{timestamp}.zip"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            manifest = {
                "backup_time": datetime.now().isoformat(),
                "snapshot_count": 0,
                "snapshot_ids": [],
            }
            for file_path in self.storage_dir.glob("*.json"):
                zf.write(file_path, file_path.name)
                manifest["snapshot_count"] += 1
                manifest["snapshot_ids"].append(file_path.stem)

            zf.writestr("_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        return str(output_path)

    def restore(self, backup_path: str, merge: bool = False) -> Dict:
        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")

        existing_ids = {f.stem for f in self.storage_dir.glob("*.json")}
        restored = 0
        skipped = 0
        overwritten = 0

        with zipfile.ZipFile(backup_path, "r") as zf:
            for name in zf.namelist():
                if name == "_manifest.json" or not name.endswith(".json"):
                    continue

                snapshot_id = Path(name).stem
                target_path = self.storage_dir / name

                if snapshot_id in existing_ids:
                    if merge:
                        skipped += 1
                        continue
                    else:
                        overwritten += 1
                else:
                    restored += 1

                with zf.open(name) as src, open(target_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read().decode("utf-8"))

        return {
            "restored": restored,
            "skipped": skipped,
            "overwritten": overwritten,
        }

    def archive_before(self, before_time: datetime, archive_path: str = None) -> Dict:
        archived_ids = []
        remaining = 0

        if archive_path is None:
            archive_dir = self.storage_dir / "archive"
            archive_dir.mkdir(exist_ok=True)
        else:
            archive_dir = Path(archive_path)
            archive_dir.mkdir(parents=True, exist_ok=True)

        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                created_at = datetime.fromisoformat(data["created_at"])
                if created_at < before_time:
                    dest = archive_dir / file_path.name
                    shutil.move(str(file_path), str(dest))
                    archived_ids.append(data["id"])
                else:
                    remaining += 1
            except (json.JSONDecodeError, KeyError):
                continue

        return {
            "archived": len(archived_ids),
            "archived_ids": archived_ids,
            "remaining": remaining,
        }

    def export_markdown(
        self,
        snapshots: List[Dict],
        output_path: str,
        title: str = "舆情快照报告",
        filter_conditions: Dict = None,
        trend_summary: Dict = None,
        follow_up_suggestions: Dict = None,
    ) -> str:
        lines = []
        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"快照数量: {len(snapshots)}")
        lines.append("")

        if filter_conditions:
            lines.append("## 筛选条件")
            lines.append("")
            parts = []
            if filter_conditions.get("artist"):
                parts.append(f"艺人: {filter_conditions['artist']}")
            if filter_conditions.get("risk_level"):
                parts.append(f"风险等级: {RISK_LABEL_MAP.get(filter_conditions['risk_level'], filter_conditions['risk_level'])}")
            if filter_conditions.get("start_time"):
                parts.append(f"起始时间: {filter_conditions['start_time']}")
            if filter_conditions.get("end_time"):
                parts.append(f"结束时间: {filter_conditions['end_time']}")
            if parts:
                lines.append("- " + " | ".join(parts))
            else:
                lines.append("- 无筛选条件（全量快照）")
            lines.append("")

        risk_counts = {}
        for s in snapshots:
            level = s["risk_level"]
            risk_counts[level] = risk_counts.get(level, 0) + 1

        lines.append("## 风险分布")
        lines.append("")
        lines.append("| 风险等级 | 数量 |")
        lines.append("|---------|------|")
        for level in ["critical", "high", "medium", "low"]:
            count = risk_counts.get(level, 0)
            lines.append(f"| {RISK_LABEL_MAP[level]} | {count} |")
        lines.append("")

        if trend_summary:
            lines.append("## 趋势摘要")
            lines.append("")
            if trend_summary.get("risk_escalated"):
                lines.append("### 风险新升高")
                lines.append("")
                for item in trend_summary["risk_escalated"]:
                    old_l = RISK_LABEL_MAP.get(item["old_level"], item["old_level"])
                    new_l = RISK_LABEL_MAP.get(item["new_level"], item["new_level"])
                    lines.append(f"- **{item['name']}**: {old_l}({item['old_score']:.1f}) → {new_l}({item['new_score']:.1f})")
                lines.append("")
            if trend_summary.get("risk_decreased"):
                lines.append("### 风险已回落")
                lines.append("")
                for item in trend_summary["risk_decreased"]:
                    old_l = RISK_LABEL_MAP.get(item["old_level"], item["old_level"])
                    new_l = RISK_LABEL_MAP.get(item["new_level"], item["new_level"])
                    lines.append(f"- **{item['name']}**: {old_l}({item['old_score']:.1f}) → {new_l}({item['new_score']:.1f})")
                lines.append("")
            if trend_summary.get("new_anomalies"):
                lines.append("### 新增异常词")
                lines.append("")
                for artist, words in trend_summary["new_anomalies"].items():
                    lines.append(f"- **{artist}**: {', '.join(words)}")
                lines.append("")
            if trend_summary.get("resolved_anomalies"):
                lines.append("### 异常词已回落")
                lines.append("")
                for artist, words in trend_summary["resolved_anomalies"].items():
                    lines.append(f"- **{artist}**: {', '.join(words)}")
                lines.append("")

        lines.append("## 快照详情")
        lines.append("")
        lines.append("| ID | 名称 | 艺人 | 创建时间 | 风险等级 | 风险分 | 讨论量 | 情绪 | 异常词 | 备注 |")
        lines.append("|----|------|------|----------|----------|--------|--------|------|--------|------|")

        for s in snapshots:
            risk_label = RISK_LABEL_MAP[s["risk_level"]]
            sentiment_label = SENTIMENT_LABEL_MAP[s["sentiment"]]
            anomaly_str = ",".join(s.get("anomaly_words", [])) if s.get("anomaly_words") else "-"
            if s.get("has_emergency"):
                anomaly_str = f"🚨 {anomaly_str}"
            elif s.get("has_spike"):
                anomaly_str = f"⚠️ {anomaly_str}"

            lines.append(
                f"| {s['id']} | {s['name']} | {s['artist_name']} | {s['created_at']} | {risk_label} | {s['risk_score']:.1f} | "
                f"{s['discussion_volume']:,} | {sentiment_label} | {anomaly_str} | {s.get('notes', '')} |"
            )

        lines.append("")
        lines.append("## 重点关注")
        lines.append("")
        high_risk = [s for s in snapshots if s["risk_level"] in ["critical", "high"]]
        if high_risk:
            lines.append("### 高风险艺人")
            lines.append("")
            for s in high_risk:
                anomaly_str = ",".join(s.get("anomaly_words", [])) if s.get("anomaly_words") else "无"
                lines.append(f"- **{s['artist_name']}** ({s['name']}): {RISK_LABEL_MAP.get(s['risk_level'], s['risk_level'])}({s['risk_score']:.1f}分)，异常词: {anomaly_str}")
        else:
            lines.append("无高风险艺人，整体态势平稳。")

        if follow_up_suggestions:
            lines.append("")
            lines.append("## 后续跟进建议")
            lines.append("")
            for artist, suggestion in follow_up_suggestions.items():
                lines.append(f"- **{artist}**: {suggestion}")

        content = "\n".join(lines)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(output_path)

    def export_json(
        self,
        snapshots: List[Dict],
        output_path: str,
        filter_conditions: Dict = None,
        trend_summary: Dict = None,
        follow_up_suggestions: Dict = None,
    ) -> str:
        export_data = {
            "generated_at": datetime.now().isoformat(),
            "count": len(snapshots),
            "filter_conditions": filter_conditions or {},
            "trend_summary": trend_summary or {},
            "follow_up_suggestions": follow_up_suggestions or {},
            "snapshots": snapshots,
        }

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

        return str(output_path)

    def delete(self, snapshot_id: str) -> bool:
        file_path = self._get_snapshot_path(snapshot_id)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def compare(self, snapshot_id1: str, snapshot_id2: str) -> Dict:
        s1 = self.load(snapshot_id1)
        s2 = self.load(snapshot_id2)

        if not s1 or not s2:
            return {"error": "One or both snapshots not found"}

        r1 = s1.analysis_result
        r2 = s2.analysis_result

        words1 = {w.word: w for w in r1.top_trending_words}
        words2 = {w.word: w for w in r2.top_trending_words}

        all_words = set(words1.keys()) | set(words2.keys())
        word_changes = []
        for word in all_words:
            w1 = words1.get(word)
            w2 = words2.get(word)
            change = {
                "word": word,
                "count1": w1.count if w1 else 0,
                "count2": w2.count if w2 else 0,
                "growth_change": (w2.growth_rate if w2 else 0) - (w1.growth_rate if w1 else 0),
            }
            word_changes.append(change)

        word_changes.sort(key=lambda x: abs(x["growth_change"]), reverse=True)

        return {
            "snapshot1": {"id": s1.id, "name": s1.name, "created_at": s1.created_at},
            "snapshot2": {"id": s2.id, "name": s2.name, "created_at": s2.created_at},
            "artist_name": s1.artist_name,
            "time_diff": (s2.created_at - s1.created_at).total_seconds() / 3600,
            "volume_change": {
                "old": r1.discussion_volume,
                "new": r2.discussion_volume,
                "diff": r2.discussion_volume - r1.discussion_volume,
                "percent": ((r2.discussion_volume - r1.discussion_volume) / r1.discussion_volume * 100) if r1.discussion_volume > 0 else 0,
            },
            "sentiment_change": {
                "old": r1.sentiment.value,
                "new": r2.sentiment.value,
                "old_score": r1.sentiment_score,
                "new_score": r2.sentiment_score,
                "diff": r2.sentiment_score - r1.sentiment_score,
            },
            "risk_change": {
                "old": r1.risk_level.value,
                "new": r2.risk_level.value,
                "old_score": r1.risk_score,
                "new_score": r2.risk_score,
                "diff": r2.risk_score - r1.risk_score,
            },
            "word_changes": word_changes[:10],
            "anomalies1": r1.anomaly_words,
            "anomalies2": r2.anomaly_words,
            "new_anomalies": [w for w in r2.anomaly_words if w not in r1.anomaly_words],
            "resolved_anomalies": [w for w in r1.anomaly_words if w not in r2.anomaly_words],
        }

    def _get_snapshot_path(self, snapshot_id: str) -> Path:
        return self.storage_dir / f"{snapshot_id}.json"

    def _snapshot_to_dict(self, snapshot: Snapshot) -> Dict:
        r = snapshot.analysis_result
        return {
            "id": snapshot.id,
            "name": snapshot.name,
            "artist_name": snapshot.artist_name,
            "created_at": snapshot.created_at.isoformat(),
            "notes": snapshot.notes,
            "analysis_result": {
                "artist_name": r.artist_name,
                "discussion_volume": r.discussion_volume,
                "volume_change": r.volume_change,
                "sentiment": r.sentiment.value,
                "sentiment_score": r.sentiment_score,
                "top_trending_words": [
                    {
                        "word": w.word,
                        "count": w.count,
                        "growth_rate": w.growth_rate,
                        "is_anomaly": w.is_anomaly,
                    }
                    for w in r.top_trending_words
                ],
                "controversy_points": [
                    {
                        "keyword": c.keyword,
                        "mentions": c.mentions,
                        "sentiment": c.sentiment.value,
                        "description": c.description,
                        "spread_potential": c.spread_potential,
                    }
                    for c in r.controversy_points
                ],
                "anomaly_words": r.anomaly_words,
                "risk_level": r.risk_level.value,
                "risk_score": r.risk_score,
                "platform": r.platform,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat(),
                "analyzed_at": r.analyzed_at.isoformat(),
                "focus_keywords": r.focus_keywords,
            },
        }

    def _dict_to_snapshot(self, data: Dict) -> Snapshot:
        r = data["analysis_result"]
        analysis_result = AnalysisResult(
            artist_name=r["artist_name"],
            discussion_volume=r["discussion_volume"],
            volume_change=r["volume_change"],
            sentiment=Sentiment(r["sentiment"]),
            sentiment_score=r["sentiment_score"],
            top_trending_words=[
                TrendingWord(**w) for w in r["top_trending_words"]
            ],
            controversy_points=[
                ControversyPoint(
                    keyword=c["keyword"],
                    mentions=c["mentions"],
                    sentiment=Sentiment(c["sentiment"]),
                    description=c["description"],
                    spread_potential=c["spread_potential"],
                )
                for c in r["controversy_points"]
            ],
            anomaly_words=r["anomaly_words"],
            risk_level=RiskLevel(r["risk_level"]),
            risk_score=r["risk_score"],
            platform=r["platform"],
            start_time=datetime.fromisoformat(r["start_time"]),
            end_time=datetime.fromisoformat(r["end_time"]),
            analyzed_at=datetime.fromisoformat(r["analyzed_at"]),
            focus_keywords=r["focus_keywords"],
        )

        return Snapshot(
            id=data["id"],
            name=data["name"],
            artist_name=data["artist_name"],
            analysis_result=analysis_result,
            created_at=datetime.fromisoformat(data["created_at"]),
            notes=data.get("notes", ""),
        )
