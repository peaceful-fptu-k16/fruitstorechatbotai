from backend.core.response_rewriter import ResponseRewriter


def test_rewriter_is_deterministic_without_llm() -> None:
    rewriter = ResponseRewriter(llm_enabled=False)

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
