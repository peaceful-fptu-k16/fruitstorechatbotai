import pytest

from backend.core.response_rewriter import ResponseRewriter


def test_rewriter_is_deterministic_without_llm() -> None:
    rewriter = ResponseRewriter(generation_mode="deterministic", llm_enabled=False)

    kwargs = {
        "base_answer": "Hôm nay Xoài Cát Hòa Lộc đang khá ổn, giá 85.000đ, còn 40.",
        "user_message": "Xoài hôm nay có gì ngon không?",
        "intent": "available_products",
        "session_id": "session-style-1",
        "language": "vi",
        "allow_follow_up": True,
    }

    first, first_mode = rewriter.rewrite(**kwargs)
    second, second_mode = rewriter.rewrite(**kwargs)

    assert first_mode == "deterministic"
    assert second_mode == "deterministic"
    assert first == second
    assert "85.000đ" in first


def test_rewriter_fallbacks_to_deterministic_when_llm_returns_none(monkeypatch) -> None:
    rewriter = ResponseRewriter(
        generation_mode="hybrid",
        llm_enabled=True,
        gemini_api_key="fake-key",
    )

    monkeypatch.setattr(rewriter, "_rewrite_with_llm", lambda **_: None)

    rewritten, mode = rewriter.rewrite(
        base_answer="Nội thành giao trong 2-4 giờ.",
        user_message="Ship bao lâu?",
        intent="faq_shipping",
        session_id="session-style-2",
        language="vi",
        allow_follow_up=True,
    )

    assert mode == "deterministic"
    assert "2-4 giờ" in rewritten


def test_rewriter_uses_gemini_when_available(monkeypatch) -> None:
    rewriter = ResponseRewriter(
        generation_mode="hybrid",
        llm_enabled=True,
        gemini_api_key="fake-key",
    )

    monkeypatch.setattr(
        rewriter,
        "_rewrite_with_llm",
        lambda **_: "Mình đã viết lại tự nhiên hơn theo Gemini và vẫn giữ nguyên dữ kiện.",
    )

    rewritten, mode = rewriter.rewrite(
        base_answer="Có nhé. Hôm nay Xoài Cát Hòa Lộc đang khá ổn.",
        user_message="Xoài hôm nay có gì ngon không?",
        intent="available_products",
        session_id="session-style-3",
        language="vi",
        allow_follow_up=True,
    )

    assert mode == "gemini"
    assert rewritten.startswith("Mình đã viết lại tự nhiên hơn")


def test_rewriter_llm_only_raises_when_no_gemini_key() -> None:
    rewriter = ResponseRewriter(
        generation_mode="llm_only",
        llm_enabled=True,
        gemini_api_key="",
    )

    with pytest.raises(RuntimeError):
        rewriter.rewrite(
            base_answer="Mình có vài gợi ý phù hợp.",
            user_message="Gợi ý cho tôi trái ngọt",
            intent="recommendation",
            session_id="session-style-4",
            language="vi",
            allow_follow_up=True,
        )


def test_rewriter_llm_only_raises_when_gemini_returns_none(monkeypatch) -> None:
    rewriter = ResponseRewriter(
        generation_mode="llm_only",
        llm_enabled=True,
        gemini_api_key="fake-key",
    )
    monkeypatch.setattr(rewriter, "_rewrite_with_llm", lambda **_: None)

    with pytest.raises(RuntimeError):
        rewriter.rewrite(
            base_answer="Mình có vài gợi ý phù hợp.",
            user_message="Gợi ý cho tôi trái ngọt",
            intent="recommendation",
            session_id="session-style-5",
            language="vi",
            allow_follow_up=True,
        )


def test_rewriter_llm_only_uses_lm_studio_when_configured(monkeypatch) -> None:
    rewriter = ResponseRewriter(
        generation_mode="llm_only",
        llm_enabled=True,
        gemini_api_key="",
        lm_studio_model_name="qwen-test",
    )
    monkeypatch.setattr(rewriter, "_rewrite_with_lm_studio", lambda **_: "Nội dung do LM Studio trả về.")

    rewritten, mode = rewriter.rewrite(
        base_answer="Mình có vài gợi ý phù hợp.",
        user_message="Gợi ý cho tôi trái ít đường",
        intent="recommendation",
        session_id="session-style-6",
        language="vi",
        allow_follow_up=True,
        rag_context=["product:12 - Nho Mẫu Đơn điểm phù hợp cao"],
    )

    assert mode == "lm_studio_strict"
    assert rewritten == "Nội dung do LM Studio trả về."


def test_lm_studio_prompt_includes_rag_grounding(monkeypatch) -> None:
    rewriter = ResponseRewriter(
        generation_mode="lm_studio",
        llm_enabled=True,
        lm_studio_model_name="qwen-test",
    )

    captured_prompt = {"value": ""}

    def _fake_call_lm_studio(*, prompt: str) -> str:
        captured_prompt["value"] = prompt
        return "Mình đã viết lại từ RAG."

    monkeypatch.setattr(rewriter, "_call_lm_studio", _fake_call_lm_studio)

    rewritten, mode = rewriter.rewrite(
        base_answer="Bản nháp có dữ kiện giá và tồn kho.",
        user_message="Gợi ý xoài ngọt",
        intent="recommendation",
        session_id="session-style-7",
        language="vi",
        allow_follow_up=False,
        rag_context=[
            "product:2: Xoài Cát Hòa Lộc giá 85.000đ, còn 40",
            "faq:shipping: giao nội thành 2-4 giờ",
        ],
    )

    assert mode == "lm_studio"
    assert rewritten == "Mình đã viết lại từ RAG."
    assert "Nguồn dữ kiện truy hồi (RAG)" in captured_prompt["value"]
    assert "product:2" in captured_prompt["value"]
