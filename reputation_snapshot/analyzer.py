import random
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from .models import (
    AnalysisResult,
    Sentiment,
    RiskLevel,
    TrendingWord,
    ControversyPoint,
    Platform,
)


POSITIVE_WORDS = [
    "优秀", "精彩", "专业", "努力", "敬业", "帅气", "美丽", "可爱", "实力",
    "努力", "正能量", "温暖", "治愈", "期待", "支持", "加油", "喜欢", "爱",
    "太棒了", "神仙", "绝了", "好棒", "优秀", "出圈", "爆款", "口碑炸裂"
]

NEGATIVE_WORDS = [
    "塌房", "抵制", "代言解约", "翻车", "黑料", "实锤", "道歉", "凉凉",
    "糊了", "封杀", "退圈", "丑闻", "绯闻", "负面", "吐槽", "差评", "质疑",
    "失望", "恶心", "垃圾", "骗子", "抄袭", "人设崩塌", "避嫌", "封杀"
]

NEUTRAL_WORDS = [
    "新剧", "直播", "活动", "代言", "综艺", "新歌", "专辑", "演唱会",
    "粉丝", "热度", "流量", "话题", "热搜", "排名", "数据", "投票",
    "采访", "发布会", "红毯", "造型", "穿搭", "妆容", "身材", "颜值"
]

CONTROVERSY_TEMPLATES = [
    ("{}疑似{}", "近期有爆料称{}相关，引发网友广泛讨论"),
    ("{}被曝{}", "多个账号发布关于{}的{}消息，传播速度较快"),
    ("{}回应{}", "针对{}事件，{}方做出回应，但网友态度分化"),
]

ANOMALY_TRIGGER_WORDS = ["塌房", "抵制", "代言解约", "翻车", "黑料", "实锤", "封杀", "凉凉", "人设崩塌", "抄袭"]


class SentimentAnalyzer:
    def analyze(self, text: str) -> Tuple[Sentiment, float]:
        pos_count = sum(1 for w in POSITIVE_WORDS if w in text)
        neg_count = sum(1 for w in NEGATIVE_WORDS if w in text)

        if pos_count > neg_count:
            score = min(1.0, 0.5 + (pos_count - neg_count) * 0.1)
            return Sentiment.POSITIVE, score
        elif neg_count > pos_count:
            score = max(-1.0, 0.5 - (neg_count - pos_count) * 0.1)
            return Sentiment.NEGATIVE, score
        else:
            return Sentiment.NEUTRAL, 0.0


class ReputationAnalyzer:
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()

    def analyze(
        self,
        artist_name: str,
        platform: str = "all",
        start_time: datetime = None,
        end_time: datetime = None,
        focus_keywords: List[str] = None,
    ) -> AnalysisResult:
        if start_time is None:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
        if end_time is None:
            end_time = datetime.now()
        if focus_keywords is None:
            focus_keywords = []

        discussion_volume = self._generate_volume(artist_name, platform)
        volume_change = self._generate_volume_change()

        sentiment, sentiment_score = self._generate_sentiment(artist_name)
        top_trending_words = self._generate_trending_words(artist_name, focus_keywords)
        controversy_points = self._generate_controversy_points(artist_name, sentiment)
        anomaly_words = self._detect_anomaly_words(top_trending_words)
        risk_level, risk_score = self._calculate_risk(
            sentiment, sentiment_score, anomaly_words, controversy_points, volume_change
        )

        return AnalysisResult(
            artist_name=artist_name,
            discussion_volume=discussion_volume,
            volume_change=volume_change,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            top_trending_words=top_trending_words,
            controversy_points=controversy_points,
            anomaly_words=anomaly_words,
            risk_level=risk_level,
            risk_score=risk_score,
            platform=platform,
            start_time=start_time,
            end_time=end_time,
            focus_keywords=focus_keywords,
        )

    def _generate_volume(self, artist_name: str, platform: str) -> int:
        base_volume = random.randint(5000, 50000)
        platform_multiplier = {
            "weibo": 1.5,
            "douyin": 1.2,
            "xhs": 0.8,
            "zhihu": 0.5,
            "douban": 0.6,
            "all": 1.0,
        }.get(platform, 1.0)
        return int(base_volume * platform_multiplier)

    def _generate_volume_change(self) -> float:
        return round(random.uniform(-30, 150), 2)

    def _generate_sentiment(self, artist_name: str) -> Tuple[Sentiment, float]:
        rand = random.random()
        if rand < 0.15:
            return Sentiment.NEGATIVE, round(random.uniform(-0.8, -0.3), 2)
        elif rand < 0.35:
            return Sentiment.NEUTRAL, round(random.uniform(-0.2, 0.2), 2)
        else:
            return Sentiment.POSITIVE, round(random.uniform(0.3, 0.9), 2)

    def _generate_trending_words(
        self, artist_name: str, focus_keywords: List[str]
    ) -> List[TrendingWord]:
        words = []
        selected_positive = random.sample(POSITIVE_WORDS, min(4, len(POSITIVE_WORDS)))
        selected_negative = random.sample(NEGATIVE_WORDS, min(2, len(NEGATIVE_WORDS)))
        selected_neutral = random.sample(NEUTRAL_WORDS, min(4, len(NEUTRAL_WORDS)))

        all_words = selected_positive + selected_negative + selected_neutral + focus_keywords
        all_words = list(set(all_words))

        for word in all_words[:10]:
            count = random.randint(100, 5000)
            growth_rate = round(random.uniform(-20, 200), 2)
            is_anomaly = word in ANOMALY_TRIGGER_WORDS and growth_rate > 50
            words.append(
                TrendingWord(
                    word=word,
                    count=count,
                    growth_rate=growth_rate,
                    is_anomaly=is_anomaly,
                )
            )

        words.sort(key=lambda x: x.growth_rate, reverse=True)
        return words

    def _generate_controversy_points(
        self, artist_name: str, sentiment: Sentiment
    ) -> List[ControversyPoint]:
        points = []
        if sentiment in [Sentiment.NEGATIVE, Sentiment.NEUTRAL]:
            num_points = random.randint(1, 3)
            for i in range(num_points):
                template_idx = random.randint(0, len(CONTROVERSY_TEMPLATES) - 1)
                template, desc_template = CONTROVERSY_TEMPLATES[template_idx]

                neg_word = random.choice(NEGATIVE_WORDS)
                keyword = template.format(artist_name, neg_word)
                description = desc_template.format(artist_name, neg_word)

                mentions = random.randint(500, 3000)
                _, score = self.sentiment_analyzer.analyze(neg_word)
                spread_potential = round(random.uniform(0.3, 0.95), 2)

                points.append(
                    ControversyPoint(
                        keyword=keyword,
                        mentions=mentions,
                        sentiment=Sentiment.NEGATIVE,
                        description=description,
                        spread_potential=spread_potential,
                    )
                )
        return points

    def _detect_anomaly_words(self, trending_words: List[TrendingWord]) -> List[str]:
        return [w.word for w in trending_words if w.is_anomaly]

    def _calculate_risk(
        self,
        sentiment: Sentiment,
        sentiment_score: float,
        anomaly_words: List[str],
        controversy_points: List[ControversyPoint],
        volume_change: float,
    ) -> Tuple[RiskLevel, float]:
        risk_score = 0.0

        if sentiment == Sentiment.NEGATIVE:
            risk_score += abs(sentiment_score) * 40
        elif sentiment == Sentiment.NEUTRAL:
            risk_score += 15

        risk_score += len(anomaly_words) * 25
        risk_score += sum(c.spread_potential * 20 for c in controversy_points)

        if volume_change > 100:
            risk_score += 15
        elif volume_change > 50:
            risk_score += 8

        risk_score = min(100, max(0, risk_score))

        if risk_score >= 75:
            return RiskLevel.CRITICAL, round(risk_score, 2)
        elif risk_score >= 50:
            return RiskLevel.HIGH, round(risk_score, 2)
        elif risk_score >= 25:
            return RiskLevel.MEDIUM, round(risk_score, 2)
        else:
            return RiskLevel.LOW, round(risk_score, 2)
