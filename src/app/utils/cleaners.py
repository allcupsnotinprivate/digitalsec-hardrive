import re
from abc import ABC, abstractmethod
from typing import Iterable, Literal

from bs4 import BeautifulSoup
from cleantext import clean as clean_text
from ftfy import fix_text
from nltk import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer

from app.utils.hash import strip_hashes


class ATextCleaner(ABC):
    @abstractmethod
    def remove_html(self, text: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def fix_encoding(self, text: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def remove_noise(self, text: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def tokenize(self, text: str) -> list[str]:
        """Split text into tokens."""

    @abstractmethod
    def remove_stopwords(self, tokens: Iterable[str]) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, tokens: Iterable[str]) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def detokenize(self, text: str) -> str:
        raise NotImplementedError

    def clean(self, text: str) -> str:
        text = self.remove_html(text)
        text = self.fix_encoding(text)
        text = self.remove_noise(text)
        tokens = self.tokenize(text)
        tokens = self.remove_stopwords(tokens)
        tokens = self.normalize(tokens)
        text_out = " ".join(tokens).strip()
        text_out = self.detokenize(text_out)
        return text_out


class BasicDocumentCleaner(ATextCleaner):
    def __init__(self, language: Literal["russian"] = "russian") -> None:
        self.language = language
        self.stop_words = set(stopwords.words(self.language))
        self.stemmer = SnowballStemmer(self.language)

    def remove_html(self, text: str) -> str:
        soup = BeautifulSoup(text, "html.parser")
        return soup.get_text(separator=" ")

    def fix_encoding(self, text: str) -> str:
        return fix_text(text)

    def remove_noise(self, text: str) -> str:
        cleaned = clean_text(
            text,
            fix_unicode=False,
            to_ascii=False,
            lower=False,
            no_line_breaks=True,
            no_urls=True,
            no_emails=True,
            no_phone_numbers=True,
            no_currency_symbols=True,
            no_emoji=True,
            no_punct=False,
            lang="ru",
        )

        cleaned = re.sub(r"[^\w\s@.+\-!?;:]", " ", cleaned)
        cleaned = re.sub(r"([!?.,;:*\-_])\1+", r"\1", cleaned)
        cleaned = strip_hashes(cleaned)

        return " ".join(cleaned.split())

    def tokenize(self, text: str) -> list[str]:
        return word_tokenize(text, language=self.language)  # type: ignore[no-any-return]

    def remove_stopwords(self, tokens: Iterable[str]) -> list[str]:
        return [t for t in tokens if t.lower() not in self.stop_words]

    def normalize(self, tokens: Iterable[str]) -> list[str]:
        return [self.stemmer.stem(t.lower()) for t in tokens]

    def detokenize(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\s+([,.;:!?])", r"\1", text)
        text = re.sub(r"\s+([)\]\}»])", r"\1", text)
        text = re.sub(r"([(\[\{«])\s+", r"\1", text)
        text = re.sub(r"([,;:])([^\s])", r"\1 \2", text)
        text = re.sub(r"([.!?])([^\s\"')\]\}»])", r"\1 \2", text)
        text = re.sub(r"\s*[-–—]\s*", " — ", text)
        text = re.sub(r"\s{2,}", " ", text).strip()
        text = re.sub(r"(\b[\w.+-]+)\s*@\s*([\w.-]+)\s*\.\s*([A-Za-z]{2,}\b)", r"\1@\2.\3", text)
        return text
