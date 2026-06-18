from typing import List, Dict
from datetime import datetime
from .models import Artist, BatchScanResult, RiskLevel, Platform
from .analyzer import ReputationAnalyzer
from .anomaly_detector import AnomalyDetector


RISK_LEVEL_ORDER = {
    RiskLevel.CRITICAL: 4,
    RiskLevel.HIGH: 3,
    RiskLevel.MEDIUM: 2,
    RiskLevel.LOW: 1,
}


class BatchScanner:
    def __init__(self):
        self.analyzer = ReputationAnalyzer()
        self.anomaly_detector = AnomalyDetector()

    def scan(
        self,
        artists: List[Artist],
        platform: str = "all",
        start_time: datetime = None,
        end_time: datetime = None,
        focus_keywords: List[str] = None,
    ) -> List[BatchScanResult]:
        results = []
        for artist in artists:
            analysis_result = self.analyzer.analyze(
                artist_name=artist.name,
                platform=platform,
                start_time=start_time,
                end_time=end_time,
                focus_keywords=focus_keywords,
            )
            anomalies = self.anomaly_detector.detect_from_result(analysis_result)
            if self.anomaly_detector.has_critical_anomaly(anomalies):
                if analysis_result.risk_level != RiskLevel.CRITICAL:
                    analysis_result.risk_level = RiskLevel.CRITICAL
                    analysis_result.risk_score = min(100, analysis_result.risk_score + 20)

            results.append(
                BatchScanResult(
                    artist=artist,
                    analysis_result=analysis_result,
                    risk_level=analysis_result.risk_level,
                    risk_score=analysis_result.risk_score,
                )
            )

        return self._sort_by_risk(results)

    def _sort_by_risk(self, results: List[BatchScanResult]) -> List[BatchScanResult]:
        return sorted(
            results,
            key=lambda r: (
                -RISK_LEVEL_ORDER[r.risk_level],
                -r.risk_score,
                -r.artist.priority,
            ),
        )

    def get_risk_summary(self, results: List[BatchScanResult]) -> Dict:
        summary = {
            "total": len(results),
            RiskLevel.CRITICAL.value: 0,
            RiskLevel.HIGH.value: 0,
            RiskLevel.MEDIUM.value: 0,
            RiskLevel.LOW.value: 0,
            "has_critical": False,
            "critical_artists": [],
        }
        for r in results:
            summary[r.risk_level.value] += 1
            if r.risk_level == RiskLevel.CRITICAL:
                summary["has_critical"] = True
                summary["critical_artists"].append(r.artist.name)
        return summary

    def load_artists_from_file(self, file_path: str) -> List[Artist]:
        artists = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(",")
                    name = parts[0].strip()
                    aliases = [a.strip() for a in parts[1:-1]] if len(parts) > 2 else []
                    priority = int(parts[-1].strip()) if len(parts) > 1 and parts[-1].strip().isdigit() else 1
                    artists.append(Artist(name=name, aliases=aliases, priority=priority))
        except FileNotFoundError:
            raise FileNotFoundError(f"艺人名单文件不存在: {file_path}")
        return artists
