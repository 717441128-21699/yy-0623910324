from typing import List, Dict
from .models import TrendingWord, AnalysisResult


ANOMALY_THRESHOLD_GROWTH = 50.0
SPIKE_THRESHOLD_GROWTH = 100.0
EMERGENCY_WORDS = ["塌房", "抵制", "代言解约", "封杀", "人设崩塌", "退圈"]

CRITICAL_WORDS = {
    "塌房": {"severity": 10, "category": "声誉危机", "emergency": True},
    "抵制": {"severity": 9, "category": "商业风险", "emergency": True},
    "代言解约": {"severity": 9, "category": "商业风险", "emergency": True},
    "翻车": {"severity": 8, "category": "声誉危机", "emergency": False},
    "黑料": {"severity": 8, "category": "声誉危机", "emergency": False},
    "实锤": {"severity": 8, "category": "声誉危机", "emergency": False},
    "封杀": {"severity": 10, "category": "职业风险", "emergency": True},
    "凉凉": {"severity": 7, "category": "人气下滑", "emergency": False},
    "人设崩塌": {"severity": 9, "category": "声誉危机", "emergency": True},
    "抄袭": {"severity": 8, "category": "法律风险", "emergency": False},
    "退圈": {"severity": 9, "category": "职业风险", "emergency": True},
    "丑闻": {"severity": 8, "category": "声誉危机", "emergency": False},
    "道歉": {"severity": 6, "category": "危机公关", "emergency": False},
    "避嫌": {"severity": 5, "category": "危机公关", "emergency": False},
}


class AnomalyDetector:
    def __init__(self):
        self.critical_words = CRITICAL_WORDS
        self.growth_threshold = ANOMALY_THRESHOLD_GROWTH
        self.spike_threshold = SPIKE_THRESHOLD_GROWTH
        self.emergency_words = EMERGENCY_WORDS

    def detect(self, trending_words: List[TrendingWord]) -> List[Dict]:
        anomalies = []
        for word in trending_words:
            if word.word in self.critical_words and word.growth_rate > self.growth_threshold:
                info = self.critical_words[word.word]
                is_spike = word.growth_rate > self.spike_threshold
                is_emergency = info.get("emergency", False)
                anomalies.append({
                    "word": word.word,
                    "count": word.count,
                    "growth_rate": word.growth_rate,
                    "severity": info["severity"],
                    "category": info["category"],
                    "severity_level": self._get_severity_level(info["severity"]),
                    "is_spike": is_spike,
                    "is_emergency": is_emergency,
                    "alert_type": self._get_alert_type(is_spike, is_emergency, word.growth_rate),
                })
        return sorted(anomalies, key=lambda x: (-x["severity"], -x["growth_rate"]))

    def detect_from_result(self, result: AnalysisResult) -> List[Dict]:
        return self.detect(result.top_trending_words)

    def _get_alert_type(self, is_spike: bool, is_emergency: bool, growth_rate: float) -> str:
        if is_emergency and is_spike:
            return "emergency_spike"
        elif is_emergency:
            return "emergency_rise"
        elif is_spike:
            return "critical_spike"
        elif growth_rate > self.spike_threshold:
            return "spike"
        else:
            return "rising"

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

    def has_emergency_anomaly(self, anomalies: List[Dict]) -> bool:
        return any(a.get("is_emergency", False) for a in anomalies)

    def has_spike_anomaly(self, anomalies: List[Dict]) -> bool:
        return any(a.get("is_spike", False) for a in anomalies)

    def get_anomaly_summary(self, anomalies: List[Dict]) -> str:
        if not anomalies:
            return "无异常词"
        emergency = [a for a in anomalies if a.get("is_emergency")]
        spike = [a for a in anomalies if a.get("is_spike") and not a.get("is_emergency")]
        rising = [a for a in anomalies if not a.get("is_spike") and not a.get("is_emergency")]
        parts = []
        if emergency:
            parts.append(f"【🚨紧急预警】{len(emergency)}个突发高危词: {','.join([a['word'] for a in emergency])}")
        if spike:
            parts.append(f"【⚠️飙升警告】{len(spike)}个快速上升词: {','.join([a['word'] for a in spike])}")
        if rising:
            parts.append(f"【📈持续关注】{len(rising)}个风险上升词: {','.join([a['word'] for a in rising])}")
        return " | ".join(parts) if parts else f"【一般关注】{len(anomalies)}个异常词"

    def get_anomaly_tag(self, word: str, anomalies: List[Dict]) -> Dict:
        for a in anomalies:
            if a["word"] == word:
                return a
        return {}
