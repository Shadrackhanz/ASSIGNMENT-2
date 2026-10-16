# Mini-Project 2 — Uganda Tax Engine

Install `pip install -r requirements.txt`, open `project2_uganda_tax_engine.ipynb` and run Restart & Run All. Run tests with `python -m pytest -q`.

The `Money` value object uses Decimal and rounds to whole UGX using ROUND_HALF_UP; float inputs are rejected. `Tax` is an abstract base class with `calculate(ctx: TaxContext) -> TaxResult`. PAYE, employee NSSF, VAT and corporate income tax are separate implementations. Payroll applies configurable Local Service Tax before PAYE per the assignment model, subtracts employee NSSF for net pay, and reports employer NSSF separately. VAT supports standard-rated, zero-rated and exempt invoices. Extension B adds a salary scenario planner.

Regulatory sources: URA PAYE rates https://ura.go.ug/en/domestic-taxes/paye-rates/ ; URA employment income https://ura.go.ug/en/employment-income/ ; URA VAT https://ura.go.ug/en/value-added-tax-vat/ ; NSSF contributions https://www.nssfug.org/about-us/mission/. The notebook uses URA FY 2026/27 PAYE bands effective 1 July 2026. This is an educational baseline, not legal/payroll advice. LST is configurable rather than a full local-authority schedule; VAT credit handling is simplified.

AI assistance was used to draft code and documentation. Review the rules, understand each cell, and declare AI use as required.
