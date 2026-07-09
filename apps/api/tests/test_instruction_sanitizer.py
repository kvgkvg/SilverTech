from __future__ import annotations

from app.services.instruction_sanitizer import humanize_button_ids

BUTTONS = [
    {"button_id": "", "vietnamese_name": ""},
    {"button_id": "time_1_min", "vietnamese_name": "1 phút"},
    {"button_id": "start", "vietnamese_name": "khởi động"},
    {"button_id": "stop_reset", "vietnamese_name": "dừng/cài đặt lại"},
    {"button_id": "up", "vietnamese_name": "tăng"},
]


def test_replaces_a_raw_button_id_with_its_vietnamese_name():
    text = "Nhấn nút time_1_min 2 lần để cài thời gian 2 phút."
    assert humanize_button_ids(text, BUTTONS) == "Nhấn nút 1 phút 2 lần để cài thời gian 2 phút."


def test_replaces_every_button_id_in_one_instruction():
    text = "Nhấn start rồi nhấn stop_reset."
    assert humanize_button_ids(text, BUTTONS) == "Nhấn khởi động rồi nhấn dừng/cài đặt lại."


def test_matches_case_insensitively():
    assert humanize_button_ids("Nhấn nút START.", BUTTONS) == "Nhấn nút khởi động."


def test_only_matches_whole_words():
    # "up" must not be eaten out of "supper", nor "start" out of "restart".
    text = "supper restart"
    assert humanize_button_ids(text, BUTTONS) == "supper restart"


def test_does_not_rewrite_text_that_already_uses_the_label():
    text = "Nhấn nút 1 phút hai lần."
    assert humanize_button_ids(text, BUTTONS) == text


def test_ignores_buttons_with_an_empty_id_or_name():
    # The seeded template carries one blank button row; it must not blow up the
    # regex nor match the empty string everywhere.
    assert humanize_button_ids("Nhấn nút gì đó.", BUTTONS) == "Nhấn nút gì đó."


def test_returns_text_unchanged_when_the_template_has_no_buttons():
    assert humanize_button_ids("Nhấn start.", []) == "Nhấn start."
