from decimal import Decimal
import pytest
from src.tax_engine import Money,PAYETax,TaxContext,NoScheduleForDateError,Invoice,calculate_vat,payroll,corporate_tax,InvalidIncomeError
def m(x): return Money(Decimal(str(x)))
@pytest.mark.parametrize("income,expected",[
 ("335000","0"),("335001","0"),("410000","15000"),("485000","33750"),
 ("10000000","2888250"),("10000001","2888250")])
def test_resident_paye_boundaries(income,expected):
    assert PAYETax().calculate(TaxContext(m(income))).tax==m(expected)
def test_nonresident_paye(): assert PAYETax().calculate(TaxContext(m(100000),resident=False)).tax==m(10000)
def test_no_schedule_raises():
    with pytest.raises(NoScheduleForDateError): PAYETax().calculate(TaxContext(m(500000),tax_date="2025-01-01"))
def test_money_rejects_float():
    with pytest.raises(TypeError): Money(1.25)
def test_vat_types_and_credit():
    r=calculate_vat([Invoice(m(1000)),Invoice(m(500),"zero-rated"),Invoice(m(300),"exempt")],m(50))
    assert r["output_vat"]==m(180) and r["net_vat_payable"]==m(130)
def test_corporate_tax():
    r=corporate_tax(m(1000000),m(400000))
    assert r["chargeable_income"]==m(600000) and r["corporate_tax"]==m(180000)
def test_payroll_nssf():
    assert payroll(m(1000000))["employee_nssf"]==m(50000)
def test_negative_income():
    with pytest.raises(InvalidIncomeError): TaxContext(m(-1))
