from typing import List, Dict
from .models import TrendingWord, AnalysisResult


ANOMALY_THRESHOLD_GROWTH = 50.0

CRITICAL_WORDS = {
    "塌房": {"severity": 10, "category": "声誉危机"},
    "抵制": {"severity": 9, "category": "商业风险"},
    "代言解约": {"severity": 9, "category": "商业风险"},
    "翻车": {"severity": 8, "category": "声誉危机"},
    "黑料": {"severity": 8, "category": "声誉危机"},
    "实锤": {"severity": 8, "category": "声誉危机"},
    "封杀": {"severity": 10, "category": "职业风险"},
    "凉凉": {"severity": 7, "category": "人气下滑"},
    "人设崩塌": {"severity": 9, "category": "声誉危机"},
    "抄袭": {"severity": 8, "category": "法律风险"},
    "退圈": {"severity": 9, "category": "职业风险"},
    "丑闻": {"severity": 8, "category": "声誉危机"},
    "道歉": {"severity": 6, "category": "危机公关"},
    "避嫌": {"severity": 5, "category": "危机公关"},
}


class AnomalyDetector:
    def __init__(self):
        self.critical_words = CRITICAL_WORDS
        self.growth_threshold = ANOMALY_THRESHOLD_GROWTH

    def detect(self, trending_words: List[TrendingWord]) -> List[Dict]:
        anomalies = []
        for word in trending_words:
            if word.word in self.critical_words and word.growth_rate > self.growth_threshold:
                info = self.critical_words[word.word]
                anomalies.append({
                    "word": word.word,
                    "count": word.count,
                    "growth_rate": word.growth_rate,
                    "severity": info["severity"],
                    "category": info["category"],
                    "severity_level": self._get_severity_level(info["severity"]),
                })
        return sorted(anomalies, key=lambda x: x["severity"], reverse=True)

    def detect_from_result(self, result: AnalysisResult) -> List[Dict]:
        return self.detect(result.top_trending_words)

    def _get_severity_level(self, severity: int) -> str:
        if severity >= 9:
            return "critical"
        elif severity >= 7:
            return "high"
        elif severity >= 5:
            return "medium"
        else:
            return "low"

    def has_critical_anomaly(self, anomalies: List[Dict]) -> bool:
        return any(a["severity_level"] == "critical" for a in anomalies)

    def get_anomaly_summary(self, anomalies: List[Dict]) -> str:
        if not anomalies:
            return "无异常词"
        critical = [a for a in anomalies if a["severity_level"] == "critical"]
        high = [a for a in anomalies if a["severity_level"] == "high"]
        parts = []
        if critical:
            parts.append(f"【严重警告】{len(critical)}个高危词: {','.join([a['word'] for a in critical])}")
        if high:
            parts.append(f"【高度关注】{len(high)}个高风险词: {','.join([a['word'] for a in high])}")
        return " | ".join(parts) if parts else f"【一般关注】{len(anomalies)}个异常词"
