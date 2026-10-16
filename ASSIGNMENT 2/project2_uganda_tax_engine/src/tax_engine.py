"""Extensible Uganda tax-engine teaching model using Decimal-only money."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

class TaxError(Exception):
    """Base tax-engine exception."""
class InvalidIncomeError(TaxError):
    """Invalid negative or malformed income."""
class NoScheduleForDateError(TaxError):
    """No configured tax schedule applies on the requested date."""

def as_decimal(value):
    """Convert values safely; floats are deliberately rejected."""
    if isinstance(value,float): raise TypeError("float is prohibited; use Decimal or a string")
    return value if isinstance(value,Decimal) else Decimal(str(value))

@dataclass(frozen=True)
class Money:
    """UGX value object; amounts round to whole shillings using ROUND_HALF_UP."""
    amount: Decimal
    currency: str="UGX"
    def __post_init__(self):
        if self.currency!="UGX": raise ValueError("Only UGX is supported")
        object.__setattr__(self,"amount",as_decimal(self.amount).quantize(Decimal("1"),rounding=ROUND_HALF_UP))
    def __add__(self,other):
        if not isinstance(other,Money): return NotImplemented
        if self.currency!=other.currency: raise ValueError("currency mismatch")
        return Money(self.amount+other.amount)
    def __sub__(self,other):
        if not isinstance(other,Money): return NotImplemented
        return Money(self.amount-other.amount)
    def __mul__(self,other):
        if isinstance(other,float): raise TypeError("float multiplier is prohibited")
        if isinstance(other,(int,Decimal)): return Money(self.amount*as_decimal(other))
        return NotImplemented
    __rmul__=__mul__
    def __lt__(self,other):
        if not isinstance(other,Money): return NotImplemented
        return self.amount<other.amount
    def __repr__(self): return f"UGX {self.amount:,.0f}"
    __str__=__repr__
    def __float__(self): raise TypeError("Money cannot be converted to float")

@dataclass(frozen=True)
class TaxContext:
    """Input values shared by tax calculation classes."""
    amount: Money
    tax_date: str="2026-10-16"
    resident: bool=True
    metadata: dict|None=None
    def __post_init__(self):
        if self.amount.amount<0: raise InvalidIncomeError("income/base cannot be negative")

@dataclass(frozen=True)
class TaxResult:
    """Tax amount and explanatory description."""
    tax: Money
    description: str
    def __post_init__(self):
        if self.tax.amount<0: raise TaxError("tax cannot be negative")

class Tax(ABC):
    """Required abstract tax interface."""
    @abstractmethod
    def calculate(self,ctx:TaxContext)->TaxResult:
        """Calculate tax for the given context."""

class PAYETax(Tax):
    """Monthly PAYE using URA FY 2026/27 bands effective 1 July 2026."""
    def __init__(self,effective_from="2026-07-01"): self.effective_from=effective_from
    def calculate(self,ctx):
        if ctx.tax_date<self.effective_from:
            raise NoScheduleForDateError(f"No PAYE schedule configured for {ctx.tax_date}")
        x=ctx.amount.amount
        if ctx.resident:
            if x<=335000: tax=Decimal(0)
            elif x<=410000: tax=(x-335000)*Decimal(".20")
            elif x<=485000: tax=Decimal(15000)+(x-410000)*Decimal(".25")
            else:
                tax=Decimal(33750)+(x-485000)*Decimal(".30")
                if x>10000000: tax+=(x-10000000)*Decimal(".10")
        else:
            if x<=335000: tax=x*Decimal(".10")
            elif x<=410000: tax=Decimal(33500)+(x-335000)*Decimal(".20")
            else:
                tax=Decimal(48500)+(x-410000)*Decimal(".30")
                if x>10000000: tax+=(x-10000000)*Decimal(".10")
        return TaxResult(Money(tax),"Monthly PAYE; URA FY 2026/27 schedule")

class NSSFEmployeeTax(Tax):
    """Employee contribution: 5% of gross wages."""
    def calculate(self,ctx): return TaxResult(Money(ctx.amount.amount*Decimal(".05")),"Employee NSSF at 5%")

class VATTax(Tax):
    """VAT for standard, zero-rated and exempt supplies."""
    def __init__(self,rate=Decimal(".18")): self.rate=as_decimal(rate)
    def calculate(self,ctx):
        kind=(ctx.metadata or {}).get("supply_type","standard")
        if kind=="standard": rate=self.rate
        elif kind in ("zero-rated","exempt"): rate=Decimal(0)
        else: raise TaxError(f"Unknown VAT supply type: {kind}")
        return TaxResult(Money(ctx.amount.amount*rate),f"VAT: {kind}")

class CorporateIncomeTax(Tax):
    """Resident company income tax at 30% of chargeable income."""
    def calculate(self,ctx): return TaxResult(Money(ctx.amount.amount*Decimal(".30")),"Corporate tax at 30%")

@dataclass(frozen=True)
class Invoice:
    """Invoice net value and VAT treatment."""
    net_amount: Money
    supply_type: str="standard"
    def __post_init__(self):
        if self.net_amount.amount<0: raise InvalidIncomeError("invoice cannot be negative")
        if self.supply_type not in {"standard","zero-rated","exempt"}: raise TaxError("invalid supply type")

def calculate_vat(invoices,input_vat=None):
    """Compute output VAT, input VAT credit, net payable and excess credit."""
    input_vat=input_vat or Money(Decimal(0)); output=Decimal(0); tax=VATTax()
    for invoice in invoices:
        output+=tax.calculate(TaxContext(invoice.net_amount,metadata={"supply_type":invoice.supply_type})).tax.amount
    return {"output_vat":Money(output),"input_vat":input_vat,
            "net_vat_payable":Money(max(Decimal(0),output-input_vat.amount)),
            "excess_input_vat":Money(max(Decimal(0),input_vat.amount-output))}

def payroll(gross,allowances=None,local_service_tax=None,resident=True,tax_date="2026-10-16"):
    """Apply LST before PAYE per assignment model; subtract employee NSSF for net pay."""
    allowances=allowances or Money(Decimal(0)); local_service_tax=local_service_tax or Money(Decimal(0))
    if min(gross.amount,allowances.amount,local_service_tax.amount)<0: raise InvalidIncomeError("payroll values cannot be negative")
    taxable=Money(max(Decimal(0),gross.amount+allowances.amount-local_service_tax.amount))
    paye=PAYETax().calculate(TaxContext(taxable,tax_date,resident))
    employee_nssf=NSSFEmployeeTax().calculate(TaxContext(gross,tax_date,resident))
    employer_nssf=Money(gross.amount*Decimal(".10"))
    net=Money(gross.amount+allowances.amount-local_service_tax.amount-paye.tax.amount-employee_nssf.tax.amount)
    return {"gross":gross,"allowances":allowances,"local_service_tax":local_service_tax,"taxable_for_paye":taxable,
            "paye":paye.tax,"employee_nssf":employee_nssf.tax,"employer_nssf":employer_nssf,"net_pay":net}

def corporate_tax(revenue,allowable_deductions):
    """Compute chargeable income less allowable deductions and corporate tax."""
    if revenue.amount<0 or allowable_deductions.amount<0: raise InvalidIncomeError("values cannot be negative")
    if allowable_deductions.amount>revenue.amount: raise InvalidIncomeError("deductions cannot exceed revenue")
    chargeable=Money(revenue.amount-allowable_deductions.amount)
    return {"chargeable_income":chargeable,"corporate_tax":CorporateIncomeTax().calculate(TaxContext(chargeable)).tax}

def tax_planner(salary_gross,allowances=None,resident=True):
    """Extension B: return a transparent salary scenario and its net-pay estimate."""
    result=payroll(salary_gross,allowances,resident=resident)
    return {"scenario":"salary","net_pay":result["net_pay"],"paye":result["paye"],"employee_nssf":result["employee_nssf"]}
