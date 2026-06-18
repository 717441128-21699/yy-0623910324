import json
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path

from .models import Snapshot, AnalysisResult, Sentiment, RiskLevel, TrendingWord, ControversyPoint


class SnapshotStorage:
    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            storage_dir = os.path.join(os.getcwd(), "snapshots")
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

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

    def list(self, artist_name: str = None) -> List[Dict]:
        snapshots = []
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if artist_name and data["artist_name"] != artist_name:
                    continue

                snapshots.append({
                    "id": data["id"],
                    "name": data["name"],
                    "artist_name": data["artist_name"],
                    "created_at": data["created_at"],
                    "risk_level": data["analysis_result"]["risk_level"],
                    "risk_score": data["analysis_result"]["risk_score"],
                    "sentiment": data["analysis_result"]["sentiment"],
                    "discussion_volume": data["analysis_result"]["discussion_volume"],
                    "notes": data.get("notes", ""),
                })
            except (json.JSONDecodeError, KeyError):
                continue

        return sorted(snapshots, key=lambda x: x["created_at"], reverse=True)

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
