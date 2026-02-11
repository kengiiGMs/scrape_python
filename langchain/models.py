"""
Modelos Pydantic para validação de FAQs estruturados.
Baseado nas especificações do doc.md para ingestão agêntica.
"""

from typing import List
from pydantic import BaseModel, Field, field_validator


class FAQItem(BaseModel):
    """Representa um item individual de FAQ estruturado."""
    
    question: str = Field(
        ...,
        description="A pergunta principal clara e direta"
    )
    
    synthetic_variations: List[str] = Field(
        ...,
        description="Lista de variações sintéticas da pergunta (coloquial, baseada em sintoma, keywords)"
    )
    
    answer: str = Field(
        ...,
        description="A resposta completa, limpa e contextualizada em Markdown"
    )
    
    category: str = Field(
        ...,
        description="Categoria do FAQ: Troubleshooting, How-To & Configuration, Billing & Account, Product Info, Policies & Compliance, ou General"
    )
    
    tags: List[str] = Field(
        ...,
        description="Lista de palavras-chave relevantes para filtro"
    )
    
    audience: str = Field(
        ...,
        description="Público alvo inferido: End-User, Admin, Developer, etc."
    )
    
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Pontuação de confiança (0.0 a 1.0) sobre a qualidade da informação extraída"
    )
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Valida se a categoria está entre as permitidas."""
        valid_categories = {
            "Troubleshooting",
            "How-To & Configuration",
            "Billing & Account",
            "Product Info",
            "Policies & Compliance",
            "General"
        }
        if v not in valid_categories:
            raise ValueError(f"Categoria '{v}' inválida. Deve ser uma de: {valid_categories}")
        return v
    
    @field_validator('synthetic_variations')
    @classmethod
    def validate_synthetic_variations(cls, v: List[str]) -> List[str]:
        """Valida se há pelo menos uma variação sintética."""
        if len(v) < 1:
            raise ValueError("Deve haver pelo menos 1 variação sintética")
        return v


class FAQResponse(BaseModel):
    """Container para a resposta completa do LLM com múltiplos FAQs."""
    
    faq_items: List[FAQItem] = Field(
        ...,
        description="Lista de itens FAQ extraídos do documento"
    )
    
    @field_validator('faq_items')
    @classmethod
    def validate_faq_items(cls, v: List[FAQItem]) -> List[FAQItem]:
        """Valida se há pelo menos um item FAQ."""
        if len(v) < 1:
            raise ValueError("Deve haver pelo menos 1 item FAQ")
        return v
