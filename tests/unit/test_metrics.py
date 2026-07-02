"""指标模块单元测试。"""
from src.metrics import (
    compute_ber, compute_fer, compute_text_match_rate, compute_checksum_pass,
)


def test_ber_zero():
    assert compute_ber([1, 0, 1, 1], [1, 0, 1, 1]) == 0.0


def test_ber_all_wrong():
    assert compute_ber([1, 1, 1, 1], [0, 0, 0, 0]) == 1.0


def test_ber_partial():
    assert compute_ber([1, 0, 1, 0], [1, 1, 1, 0]) == 0.25


def test_ber_empty():
    assert compute_ber([], []) == 0.0


def test_fer_single_pass():
    assert compute_fer(True) == 0.0


def test_fer_single_fail():
    assert compute_fer(False) == 1.0


def test_fer_multiple():
    assert compute_fer([True, True, False, True]) == 0.25


def test_fer_empty_list():
    assert compute_fer([]) == 0.0


def test_text_match_equal():
    assert compute_text_match_rate("abc", "abc") == 1.0


def test_text_match_partial():
    assert compute_text_match_rate("abcd", "abce") == 0.75


def test_text_match_empty():
    assert compute_text_match_rate("", "") == 1.0


def test_checksum_pass_match():
    assert compute_checksum_pass([1, 0, 1], [1, 0, 1]) is True


def test_checksum_pass_mismatch():
    assert compute_checksum_pass([1, 0, 1], [1, 0, 0]) is False
