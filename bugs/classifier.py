"""Bug classifier (Fase 3b).

Real impl = local multilingual embeddings (fastembed, no torch) + similarity to
category anchor phrases with a margin, used as a candidate RANKER/pre-filter
(humans confirm via moderation). FakeClassifier keeps tests offline.
"""
import functools
from dataclasses import dataclass

from django.conf import settings

CATEGORIES = ["crash", "graphics", "performance", "progression", "online", "other"]


@dataclass
class Classification:
    is_bug: bool
    category: str
    score: float


class FakeClassifier:
    KEYWORDS = {
        "crash": ["crash", "freeze", "trava", "congela"],
        "performance": ["fps", "lag", "stutter", "loading", "carreg", "otimiz"],
        "online": ["server", "servidor", "connect", "conect", "matchmaking", "online"],
        "graphics": ["texture", "textura", "glitch", "grafic", "visual"],
        "progression": ["quest", "save", "softlock", "progress", "missão"],
    }

    def classify(self, texts):
        out = []
        for t in texts:
            low = (t or "").lower()
            cat = next((c for c, kws in self.KEYWORDS.items() if any(k in low for k in kws)), None)
            if cat:
                out.append(Classification(True, cat, 0.9))
            elif any(k in low for k in ("bug", "broken", "bugad", "quebrad")):
                out.append(Classification(True, "other", 0.6))
            else:
                out.append(Classification(False, "other", 0.0))
        return out


class EmbeddingClassifier:
    ANCHORS = {
        "crash": "the game crashes, freezes, closes to desktop, black screen on launch",
        "graphics": "graphical glitches, textures not loading, visual bugs, flickering",
        "performance": "low fps, stutter, lag, frame drops, long loading screens",
        "progression": "quest broken, cannot progress, save corrupted, softlock, stuck",
        "online": "servers down, cannot connect, disconnects, matchmaking broken",
        "other": "game breaking bug, buggy, glitchy, broken mechanics",
    }
    NEG = ["amazing game, great story and characters, beautiful, i love it, recommend, fun",
           "boring, overpriced, disappointing, not worth it, bad writing, mid"]
    MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    THRESHOLD = 0.42
    MARGIN = 0.03

    def __init__(self):
        import numpy as np
        from fastembed import TextEmbedding
        self._np = np
        self._model = TextEmbedding(self.MODEL)
        self._cats = list(self.ANCHORS)
        self._cat_vecs = self._embed([self.ANCHORS[c] for c in self._cats])
        self._neg_vecs = self._embed(self.NEG)

    def _embed(self, texts):
        v = self._np.array(list(self._model.embed(list(texts))))
        return v / (self._np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)

    def classify(self, texts):
        texts = list(texts)
        if not texts:
            return []
        vecs = self._embed(texts)
        cat_sim = vecs @ self._cat_vecs.T
        neg_sim = (vecs @ self._neg_vecs.T).max(1)
        out = []
        for i in range(len(texts)):
            j = int(cat_sim[i].argmax())
            best = float(cat_sim[i, j])
            neg = float(neg_sim[i])
            out.append(Classification(best >= self.THRESHOLD and (best - neg) >= self.MARGIN,
                                      self._cats[j], round(best - neg, 3)))
        return out


@functools.lru_cache(maxsize=2)
def _build_classifier(kind):
    return FakeClassifier() if kind == "fake" else EmbeddingClassifier()


def get_classifier():
    return _build_classifier(getattr(settings, "BUGS_CLASSIFIER", "embedding"))
