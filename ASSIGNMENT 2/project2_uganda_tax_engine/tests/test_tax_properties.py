import pytest
hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st
from decimal import Decimal
from src.tax_engine import Money, PAYETax, TaxContext

@given(st.integers(min_value=0, max_value=100_000_000))
def test_paye_is_nonnegative_and_never_exceeds_income(income):
    tax=PAYETax().calculate(TaxContext(Money(Decimal(income)))).tax.amount
    assert tax >= 0
    assert tax <= income

@given(st.integers(min_value=0, max_value=100_000_000), st.integers(min_value=0, max_value=100_000_000))
def test_resident_paye_is_monotonic(a,b):
    low,high=sorted((a,b))
    t_low=PAYETax().calculate(TaxContext(Money(Decimal(low)))).tax.amount
    t_high=PAYETax().calculate(TaxContext(Money(Decimal(high)))).tax.amount
    assert t_low <= t_high
