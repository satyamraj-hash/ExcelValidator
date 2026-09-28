"""
Fintech, LMS, LOS & Banking Domain Knowledge Base
=================================================

Comprehensive domain knowledge for an AI assistant working on:

- Loan Management System (LMS)
- Loan Origination System (LOS)
- Loan lifecycle
- Customer / Applicant / Co-Applicant / Guarantor
- Loan Application
- Sanction / Disbursement
- EMI / Repayment Schedule / Amortization
- Principal / Interest / Outstanding / Due / Received / Pending
- Part Payment / Foreclosure / Settlement
- DPD / SMA / NPA / Asset Classification
- NACH / eNACH / UMRN / SPDC / PDC / Bounce
- Charges / GST / Taxes / Fees
- Collateral / LTV / Valuation / Mortgage / Hypothecation
- Disbursal Breakup / Deductions / Net Disbursed
- Bank Details / Payments / Receipts
- Excess Money / Advance EMI / Refund
- Accounting / GL / Accrual concepts
- Co-lending
- Migration validation
- Excel migration data quality
- Common LMS migration errors
- SynoFin/SynoFiN terminology

This module is intended to help an AI assistant:
1. Understand user questions.
2. Recognize fintech terminology and aliases.
3. Explain concepts.
4. Understand relationships between LMS fields.
5. Support migration validation.
6. Identify common data inconsistencies.
7. Suggest validation logic without inventing unsupported business rules.
"""

from typing import Dict, Optional, List, Tuple


# ============================================================
# 1. CORE FINTECH DICTIONARY
# ============================================================

FINTECH_DICTIONARY: Dict[str, str] = {

    # --------------------------------------------------------
    # LMS / LOS
    # --------------------------------------------------------

    "lms": """
**Loan Management System (LMS)**

An LMS manages a loan after origination/disbursement and throughout
its lifecycle until closure.

Typical LMS responsibilities:
- Loan account creation
- Loan/customer mapping
- Disbursement
- Repayment schedule generation
- EMI tracking
- Principal and interest tracking
- Payment/receipt processing
- NACH presentation and realization
- Bounce management
- Charges and penalties
- Part-payment
- Foreclosure/pre-closure
- DPD calculation
- Asset classification
- NPA tracking
- Loan closure
- Settlement
- Accounting and GL integration

Typical migration entities:
Customer → Loan Application → Loan → Disbursement → Repayment Schedule
→ Payments/Receipts → Charges → Excess Money → Closure/Foreclosure.
""",

    "los": """
**Loan Origination System (LOS)**

LOS handles the pre-disbursement lifecycle of a loan.

Typical stages:
- Lead generation
- Enquiry
- DDE / Data Entry
- Document collection
- Credit assessment
- PD / Personal Discussion
- Verification
- Sanction
- Review
- Recommendation
- Disbursement approval
- Disbursement

LOS is primarily focused on originating and approving the loan.
LMS generally takes over after loan creation/disbursement.
""",

    "dde": """
**DDE - Data Entry / Data Entry Executive stage**

The stage where borrower, loan, income, KYC, collateral and other
application information is captured and prepared for underwriting.
""",

    "pd": """
**PD - Personal Discussion**

A borrower interaction/verification stage used to assess the applicant,
business, repayment ability, profile and other underwriting factors.

A PD may contain:
- Questions
- Answers
- Remarks
- Audio recording
- Verification observations
- Risk indicators.
""",

    "sanction": """
**Sanction**

The approved loan decision containing sanctioned terms such as:
- Sanctioned amount
- Interest rate
- Tenure
- EMI
- Product/scheme
- Repayment frequency
- Charges
- Conditions/terms

Sanction does not necessarily mean that the loan has already been
disbursed.
""",

    # --------------------------------------------------------
    # CUSTOMER / PARTY
    # --------------------------------------------------------

    "customer": """
**Customer / Borrower**

The person or entity associated with a loan.

Common roles:
- Applicant
- Co-applicant
- Guarantor
- Borrower
- Co-borrower
- Reference/contact

Important migration principle:
A customer may be associated with multiple loans and multiple roles.
Do not automatically assume that every customer_id must be unique across
the complete migration dataset.
""",

    "applicant": """
**Applicant**

The primary person/entity applying for the loan.

The applicant normally becomes the primary borrower when the loan
is sanctioned/disbursed.
""",

    "coapplicant": """
**Co-Applicant**

A person/entity jointly associated with the loan application.

A co-applicant may contribute income, ownership, repayment obligation,
or credit support depending on the product/business rules.
""",

    "guarantor": """
**Guarantor**

A person/entity providing a guarantee for the borrower's obligations.

The guarantor is not automatically the same as a co-applicant.
Their legal and repayment responsibilities depend on the loan structure.
""",

    "kyr": """
**KYC - Know Your Customer**

Customer identification and verification information.

Common KYC fields:
- PAN
- Aadhaar
- Passport
- Voter ID
- Driving Licence
- Address proof
- Identity proof
- Date of birth
- Name
""",

    "pan": """
**PAN - Permanent Account Number**

A tax identifier issued in India.

In migration validation:
- Check format where applicable.
- Check missing values.
- Check unexpected duplicates.
- Do not assume duplicate PAN always means duplicate customer.
A customer may legitimately have multiple loan relationships.
""",

    # --------------------------------------------------------
    # LOAN
    # --------------------------------------------------------

    "loan": """
**Loan**

A financial facility provided to a borrower under defined terms.

Important loan attributes:
- Loan ID
- Loan application number
- Customer
- Product
- Scheme
- Sanction amount
- Disbursed amount
- Interest rate
- Tenure
- EMI
- Disbursement date
- Maturity date
- Status
- Asset classification
- Outstanding amount
""",

    "loan_application": """
**Loan Application**

The application-level record from LOS/LMS.

Common fields:
- loan_application_number
- customer_id
- applicant
- product
- scheme
- branch
- loan amount
- tenure
- interest rate
- FOIR
- LTV
- purpose
- application date
- sanction details
- status

Loan application data must be correctly mapped to the corresponding
customer and loan.
""",

    "loan_id": """
**Loan ID**

A unique identifier representing a loan account in the LMS.

During migration:
- It should be mapped consistently across all loan-level sheets.
- The same loan_id should connect repayment, charges, payments,
  collateral, disbursement and other related records.
""",

    "product": """
**Product**

The broad category of the loan.

Examples:
- Personal Loan
- Business Loan
- Home Loan
- Loan Against Property
- Agriculture Loan
- Vehicle Loan
- Education Loan

A product can contain multiple schemes.
""",

    "scheme": """
**Scheme**

A specific configuration/variant under a product.

A scheme may define:
- Interest rate
- Tenure
- Repayment frequency
- Charges
- Eligibility
- Accounting treatment
- Product behavior

Do not assume scheme codes are interchangeable with scheme names.
Migration should generally use the target system's valid production codes.
""",

    # --------------------------------------------------------
    # DISBURSEMENT
    # --------------------------------------------------------

    "disbursement": """
**Disbursement**

The process of releasing sanctioned loan funds to the borrower or
other eligible recipients.

Disbursement may be:
- Single tranche
- Multiple tranche
- Net of deductions
- Direct to borrower
- Direct to seller/vendor
- Adjusted against charges
- Adjusted against advance EMI or other components
""",

    "tranche": """
**Tranche**

A portion of a loan amount disbursed separately.

A single loan may have multiple disbursement tranches.

Each tranche may have:
- Disbursement date
- Amount
- Recipient
- Deductions
- Adjustments
- Reference number
""",

    "disbursal_breakup": """
**Disbursal Breakup**

Breaks the sanctioned/disbursed amount into:
- Gross disbursement
- Charges/deductions
- Adjustments
- Net disbursed amount

Conceptually:

Gross Amount
- Deductions
- Adjustments
= Net Disbursed Amount

Exact calculation depends on the target LMS configuration.
""",

    "net_disbursed": """
**Net Disbursed Amount**

The amount actually released after applicable deductions/adjustments.

Typical conceptual relationship:

Net Disbursed = Gross Disbursement - Adjusted Deductions

The exact business calculation must follow the target LMS configuration.
""",

    # --------------------------------------------------------
    # EMI / REPAYMENT
    # --------------------------------------------------------

    "emi": """
**EMI - Equated Monthly Instalment**

A periodic payment generally consisting of:
- Principal component
- Interest component

For a standard reducing-balance loan:

EMI = P × r × (1+r)^n / ((1+r)^n - 1)

Where:
P = principal
r = periodic interest rate
n = number of installments

Actual LMS calculations may vary for:
- Daily reducing balance
- Monthly reducing balance
- Flat rate
- Broken period interest
- Different repayment frequencies
- Moratorium
- Part-payment
- Rate changes
""",

    "principal": """
**Principal**

The original or outstanding amount of the loan excluding interest.

Repayment generally reduces principal outstanding.

Typical relationship:

Closing Principal = Opening Principal - Principal Repaid

Additional adjustments such as part-payment, capitalization or reversals
may modify this relationship.
""",

    "interest": """
**Interest**

The financing cost charged on outstanding principal.

Interest can depend on:
- Interest rate
- Outstanding principal
- Number of days
- Repayment frequency
- Interest method
- Effective rate
- Broken period
- Moratorium
- Product configuration
""",

    "repayment_schedule": """
**Repayment Schedule**

A schedule containing the expected installments over the loan tenure.

Common columns:
- loan_id
- repayment_schedule_id
- due_date
- installment_number
- installment_amount
- opening_balance
- principal
- interest
- principal_outstanding
- interest_rate
- status
- received_amount
- principal_due
- interest_due
- pending_amount
- closing_balance

The exact column names can differ between systems.
""",

    "opening_balance": """
**Opening Balance**

The loan/repayment balance at the beginning of an installment period.

For a normal amortization schedule:

Opening Balance of current installment
≈ Closing Balance of previous installment

Exceptions can occur because of:
- Part-payment
- Foreclosure
- Adjustments
- Reversal
- Rescheduling
- Moratorium
- Interest capitalization
""",

    "closing_balance": """
**Closing Balance**

The outstanding balance after applying the relevant installment
transactions/adjustments.

For a fully closed/foreclosed loan, the closing balance of the
final relevant schedule row is generally expected to be 0.

A non-zero closing balance in a closed loan should be investigated,
but the exact expected value depends on the loan status and transaction
history.
""",

    "principal_outstanding": """
**Principal Outstanding**

The remaining principal that the borrower owes.

Conceptually:

Principal Outstanding
= Previous Principal Outstanding
- Principal Repaid
- Eligible Principal Adjustments

Part-payment generally reduces principal outstanding.
""",

    "received_amount": """
**Received Amount**

The amount actually received/realized against a repayment schedule
or installment.

It should not automatically be assumed equal to installment_amount.

Possible scenarios:
- Full payment
- Partial payment
- Overpayment
- Advance payment
- Adjustment
- Reversal
- Foreclosure
""",

    "principal_due": """
**Principal Due**

The unpaid principal portion currently due.

For a fully paid installment, principal_due is normally 0.

For a pending/unpaid installment, principal_due may contain the unpaid
principal component.
""",

    "interest_due": """
**Interest Due**

The unpaid interest portion currently due.

For a fully paid installment, interest_due is normally 0.
""",

    "pending_amount": """
**Pending Amount**

The amount remaining to be paid for a schedule/installment.

Conceptually:

Pending Amount
= Amount Due - Amount Received/Adjusted

Exact calculation depends on how the target LMS handles:
- Partial payment
- Overpayment
- Advance payment
- Refund
- Reversal
- Adjustment
""",

    "amortization": """
**Amortization**

The gradual allocation of loan repayments between interest and principal.

In a standard reducing-balance schedule:
- Earlier EMIs generally contain a higher interest component.
- As principal reduces, interest generally reduces.
- Principal component generally increases over time.

This pattern can differ for flat-rate products.
""",

    # --------------------------------------------------------
    # PAYMENT / RECEIPT
    # --------------------------------------------------------

    "payment": """
**Payment**

A financial transaction representing money received from or on behalf
of the borrower.

Payment processing may result in:
- Receipt creation
- Schedule allocation
- Principal adjustment
- Interest adjustment
- Charge adjustment
- Excess money
- Refund
- Reversal
""",

    "receipt": """
**Receipt**

A record confirming/representing a received payment.

A receipt can be linked to:
- Loan
- Customer
- Payment date
- Amount
- Payment mode
- Instrument/reference
- Schedule allocation
- Charges
- Principal
- Interest

Receipt amount and repayment schedule received amount should be
reconciled according to the target system's allocation logic.
""",

    "excess_money": """
**Excess Money**

An amount received that is not fully consumed by the intended dues.

Possible reasons:
- Overpayment
- Advance payment
- Excess receipt
- Payment allocation mismatch

Depending on business configuration, excess money may be:
- Carried forward
- Adjusted against future dues
- Treated as advance EMI
- Refunded
- Used during foreclosure/closure
""",

    "advance_emi": """
**Advance EMI**

An EMI received before its normal due date or an amount treated as
advance against future installments.

It should be distinguished from:
- Excess payment
- Overpayment
- Principal prepayment
- Part-payment

The exact treatment depends on LMS configuration.
""",

    "refund": """
**Refund**

Money returned to the borrower.

Common scenarios:
- Overpayment
- Excess money
- Failed/reversed transaction
- Foreclosure excess
- Cancellation
- Other refundable balance

Example:

Original payable amount = 750
Amount received = 3000

Potential excess = 2250

The actual treatment should follow business rules, e.g. refund/IRR refund
where configured.
""",

    # --------------------------------------------------------
    # PART PAYMENT / FORECLOSURE
    # --------------------------------------------------------

    "part_payment": """
**Part Payment (PP)**

A payment made outside the normal EMI schedule to reduce outstanding
principal.

Typical impact:
- Principal outstanding decreases.
- Future repayment schedule may be recalculated.
- EMI may reduce, tenure may reduce, or both depending on configuration.
- Interest may reduce because outstanding principal reduces.

Migration note:
Part-payment rows should not automatically be treated as normal EMI rows.
Legacy systems may represent them using special installment/status values.
""",

    "pp": """
**PP = Part Payment**

A lump-sum principal reduction outside the normal EMI schedule.

Important:
A PP transaction is not necessarily a regular installment.
Validation logic should consider the source system's representation.
""",

    "foreclosure": """
**Foreclosure / Pre-Closure (FC)**

Complete settlement of the loan before the scheduled maturity date.

A foreclosure transaction can include:
- Principal outstanding
- Accrued interest
- Foreclosure charges
- GST/taxes
- Other dues
- Adjustments
- Excess money

For a fully foreclosed loan:
- The relevant final balance should generally be zero.
- Future active installments should not remain payable after closure.
- Any remaining excess/refund should be handled separately.

Always distinguish foreclosure from settlement/write-off.
""",

    "fc": """
**FC = Foreclosure**

A loan closure transaction where the outstanding liability is settled
before contractual maturity.
""",

    "settlement": """
**Settlement**

A negotiated closure where the borrower pays an agreed amount that may
differ from the total contractual outstanding.

Settlement is different from normal foreclosure.

Settlement may involve:
- Waiver
- Discount
- Principal adjustment
- Interest waiver
- Charge waiver
- Settlement amount
- Closure status
""",

    # --------------------------------------------------------
    # MORATORIUM
    # --------------------------------------------------------

    "moratorium": """
**Moratorium**

A period during which regular repayment obligations may be deferred.

Interest treatment can vary:
- Interest paid during moratorium
- Interest capitalized
- Interest accumulated and added later
- Interest added to subsequent installments

Migration should preserve the source system's actual treatment.
""",

    # --------------------------------------------------------
    # DPD / NPA
    # --------------------------------------------------------

    "dpd": """
**DPD - Days Past Due**

Number of days an amount remains overdue after its contractual due date.

Typical regulatory SMA buckets in India:
- SMA-0: up to 30 days
- SMA-1: more than 30 and up to 60 days
- SMA-2: more than 60 and up to 90 days
- NPA: generally when dues remain overdue for more than 90 days,
  subject to applicable regulatory rules.

DPD is based on overdue obligations, not simply loan age.
""",

    "sma": """
**SMA - Special Mention Account**

A classification used before an account becomes NPA.

Common buckets:
- SMA-0: up to 30 days overdue
- SMA-1: more than 30 and up to 60 days overdue
- SMA-2: more than 60 and up to 90 days overdue

Applicable regulatory requirements and product-specific rules should
always be considered.
""",

    "npa": """
**NPA - Non-Performing Asset**

A loan classified as non-performing when applicable regulatory criteria
are met, commonly based on overdue status exceeding 90 days for relevant
principal/interest dues.

Typical asset classifications after NPA classification may include:
- Substandard
- Doubtful
- Loss

Exact classification and provisioning treatment depends on applicable
regulations and institution policy.
""",

    "asset_classification": """
**Asset Classification**

Classification of a loan/account based on its repayment performance.

Common values:
- regular
- substandard
- doubtful
- loss

Source data may use different capitalization or naming conventions.

Migration validation should distinguish:
- Source value
- Target accepted value
- Display label

For example, `residential_flat` and `Residential Flat` may represent
the same business concept while being different strings.
""",

    # --------------------------------------------------------
    # NACH / BANKING
    # --------------------------------------------------------

    "nach": """
**NACH - National Automated Clearing House**

An NPCI-operated electronic payment system supporting recurring/bulk
transactions.

For LMS:
- Used for recurring EMI debit.
- Mandate is linked to a bank account.
- Mandate may have a maximum debit amount.
- UMRN identifies the mandate.

Common fields:
- UMRN
- Account number
- IFSC
- Bank name
- Mandate amount
- Frequency
- Start date
- End date
- Status
""",

    "enach": """
**e-NACH**

Electronic mandate registration used for automated recurring debits.

It provides a digital mechanism for setting up recurring loan repayment
mandates.
""",

    "umrn": """
**UMRN - Unique Mandate Reference Number**

A unique identifier for an NACH mandate.

Migration checks may include:
- Missing UMRN
- Duplicate UMRN
- Invalid mapping
- Incorrect status
- Same mandate mapped to unexpected accounts/customers

A duplicate UMRN does not automatically prove that the data is invalid;
the expected uniqueness scope should be confirmed.
""",

    "spdc": """
**SPDC - Security Post-Dated Cheque**

Security cheque collected as part of loan security/repayment arrangements.

SPDC data can contain:
- Cheque number
- Bank
- Account
- IFSC
- Date
- Amount
- Status
""",

    "pdc": """
**PDC - Post-Dated Cheque**

A cheque dated for a future date, commonly collected for repayment/security
purposes.

PDC and SPDC are related concepts but should not automatically be treated
as identical in every business process.
""",

    "bounce": """
**Bounce**

A payment/mandate/instrument failure where the expected payment is not
successfully realized.

Possible reasons:
- Insufficient funds
- Account closed
- Mandate issue
- Technical failure
- Incorrect bank details
- Payment rejected

A bounce may result in:
- Bounce charges
- Additional overdue
- DPD increase
- Re-presentation
- Collection action
""",

    "clearing": """
**Clearing**

The process through which a payment/instrument is processed between
financial institutions before final settlement/realization.
""",

    # --------------------------------------------------------
    # COLLATERAL
    # --------------------------------------------------------

    "collateral": """
**Collateral**

An asset pledged/secured against a loan.

Examples:
- Property
- Vehicle
- Machinery
- Gold
- Inventory
- Equipment

Common collateral data:
- Asset type
- Asset value
- Market value
- Forced sale value
- Valuation date
- Owner
- Registration details
- Address
- Property age
- Property status
""",

    "ltv": """
**LTV - Loan-to-Value Ratio**

Ratio of loan amount to collateral value.

Formula:

LTV % = (Loan Amount / Collateral Value) × 100

Example:
Loan = 50 lakh
Collateral value = 100 lakh

LTV = 50%

The exact denominator and loan amount used can vary by product policy.
""",

    "valuation": """
**Valuation**

Assessment of the monetary value of collateral/asset.

Valuation may include:
- Market value
- Forced sale value
- Distress value
- Realizable value
- Valuation date
- Valuer details

The value used for LTV must follow the relevant product/business rule.
""",

    "mortgage": """
**Mortgage**

A security interest created over immovable property to secure a loan.

The borrower generally retains possession, while the lender obtains
rights over the property as security according to the legal arrangement.
""",

    "hypothecation": """
**Hypothecation**

A charge/security interest over movable assets where possession generally
remains with the borrower.

Common examples:
- Vehicles
- Machinery
- Equipment
- Inventory

It differs from mortgage, which generally concerns immovable property.
""",

    # --------------------------------------------------------
    # UNDERWRITING
    # --------------------------------------------------------

    "foir": """
**FOIR - Fixed Obligations to Income Ratio**

Measures the borrower's fixed financial obligations relative to income.

Conceptual formula:

FOIR % = (Fixed Obligations / Income) × 100

A higher FOIR generally means a larger portion of income is already
committed to obligations.

Exact formula and included obligations depend on lender policy.
""",

    "cibil": """
**CIBIL / Credit Score**

A credit score used to assess an individual's credit history.

Common Indian consumer credit scores are represented on a 300-900 scale.

The score is only one component of underwriting and should not be treated
as the complete credit decision.
""",

    "credit_score": """
**Credit Score**

A numerical representation derived from credit history.

It may influence underwriting along with:
- Income
- FOIR
- LTV
- Existing obligations
- Banking behavior
- Employment/business profile
- Bureau history
- Risk policy
""",

    # --------------------------------------------------------
    # CHARGES / GST
    # --------------------------------------------------------

    "charges": """
**Loan Charges**

Additional amounts charged to the borrower.

Examples:
- Processing fee
- Documentation fee
- Login fee
- Upfront fee
- Foreclosure charge
- Bounce charge
- Penal charge
- Legal charge
- Valuation charge
- Insurance/Hospicash charge
- Platform fee

Charge records may contain:
- Charge type
- Charge amount
- Tax/GST
- Total amount
- Waiver
- Paid status
- Receipt mapping
""",

    "processing_fee": """
**Processing Fee**

A fee charged for processing/underwriting a loan application.

It may be:
- Deducted from disbursement
- Collected upfront
- Collected separately
- Capitalized/adjusted depending on product configuration
""",

    "gst": """
**GST**

Goods and Services Tax applicable to eligible goods/services and charges
as per applicable Indian tax rules.

For LMS charge migration, distinguish:
- Base charge
- GST amount
- Total charge including GST

Do not assume every financial amount is GST-applicable.
""",

    "foreclosure_charge": """
**Foreclosure Charge**

A charge applicable to eligible early loan closure according to the
loan/product terms and applicable rules.

It may be represented separately from principal and interest.
""",

    "penal_charge": """
**Penal Charge / Penal Interest**

Additional amount applicable due to specified repayment defaults or
delays, subject to product terms and applicable regulations.

Do not automatically calculate penalties unless the configured business
rule is known.
""",

    "hospicash": """
**Hospicash**

An insurance/benefit-related charge or product component that may appear
in LMS migration data depending on the lender's configuration.

Important migration checks:
- Charge type mapping
- Amount
- GST
- Product applicability
- Target production configuration
- Charge creation/mapping
""",

    # --------------------------------------------------------
    # TAX
    # --------------------------------------------------------

    "tds": """
**TDS - Tax Deducted at Source**

Tax deducted at source under applicable tax provisions.

In a financial system, conventions may include:
- no_tds
- gross_tds
- net_tds

Always validate which convention the target LMS expects before migration.
""",

    # --------------------------------------------------------
    # CO-LENDING
    # --------------------------------------------------------

    "colending": """
**Co-Lending**

A financing arrangement where multiple regulated lenders jointly finance
a loan according to an agreed structure.

Example:
Primary lender = 90%
Co-lender = 10%

Depending on the arrangement, lenders may share:
- Principal
- Interest
- Risk
- Collections
- Accounting
- Servicing responsibilities

Migration must preserve the configured participation/share ratios.
""",

    "lender_share": """
**Lender Share**

The portion of principal/economic participation belonging to a lender in
a co-lending arrangement.

Example:
Total principal = 10,00,000
Lender A share = 90%
Lender B share = 10%

A = 9,00,000
B = 1,00,000

Actual accounting treatment may include additional components.
""",

    # --------------------------------------------------------
    # ACCOUNTING
    # --------------------------------------------------------

    "gl": """
**GL - General Ledger**

Accounting structure used to record financial transactions.

Examples of GL categories:
- Principal receivable
- Interest income
- Charges
- GST
- Bank
- Suspense
- Refund
- Accrual
- Write-off

GL codes are institution-specific and should not be guessed during
migration.
""",

    "accrual": """
**Accrual**

Recognition of income/expense in the accounting period in which it is
earned/incurred rather than only when cash is received.

In LMS:
- Interest accrual
- Penal accrual
- Charge accrual
- Other income accrual

Actual accounting behavior depends on configuration.
""",

    "irr": """
**IRR - Internal Rate of Return**

A rate used to evaluate the return represented by loan cash flows.

Loan cash flows may include:
- Disbursement
- EMI
- Charges
- Fees
- Adjustments
- Refunds

IRR calculations are sensitive to transaction dates and cash-flow values.
""",

    "irr_refund": """
**IRR Refund**

A refund/adjustment mechanism used in some LMS/accounting configurations
for excess or over-collected amounts while preserving the required
cash-flow/accounting treatment.

Example scenario:
Original payable amount = 750
Amount received = 3000
Potential excess = 2250

The exact treatment should follow the configured accounting process.
""",

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    "paid": """
**Paid**

Indicates that the relevant amount/obligation has been fully satisfied.

For a fully paid installment, common expectations are:
- No remaining principal due
- No remaining interest due
- Pending amount = 0

Exact fields depend on the target LMS.
""",

    "pending": """
**Pending**

Indicates that an amount/obligation remains unpaid or unresolved.

A pending installment may have:
- Principal due
- Interest due
- Pending amount
- Zero/partial received amount
""",

    "outstanding": """
**Outstanding**

Indicates an amount that remains payable.

Outstanding can refer to:
- Principal outstanding
- Interest outstanding
- Installment outstanding
- Total loan outstanding
- Charge outstanding

The exact meaning depends on the field/context.
""",

    "closed": """
**Closed**

A loan/account that has completed its lifecycle and has no remaining
contractual obligation according to the LMS.

For a properly closed loan, relevant outstanding balance should generally
be zero, subject to any separate refund/adjustment process.
""",

    "active": """
**Active**

A loan that remains operational and has not been fully closed.

Active does not necessarily mean that every installment is current;
an active loan can also be overdue.
""",

    # --------------------------------------------------------
    # MIGRATION
    # --------------------------------------------------------

    "migration": """
**LMS Data Migration**

Moving historical/legacy loan data into a new LMS.

Typical migration flow:

1. Source data received
2. Data profiling
3. Mapping
4. Transformation
5. Validation
6. Pre-Prod migration
7. Frontend/API/DB validation
8. Issue identification
9. Data correction
10. Re-migration
11. Production migration
12. Post-migration validation

Common migration entities:
- Customer
- Loan Application
- Loan
- Collateral
- Disbursal
- Repayment Schedule
- Payments
- Receipts
- Loan Charges
- Bank Details
- NACH Details
- SPDC/PDC
- Excess Money
""",

    "remigration": """
**Re-Migration**

Migration of corrected data again after issues were identified in the
previous migration.

Typical reasons:
- Incorrect source data
- Incorrect mapping
- Target configuration issue
- Missing records
- Changed repayment schedule
- Updated charges
- Incorrect receipts
- Updated disbursal breakup

Before re-migration, identify whether the correction is:
1. Source-data correction
2. Transformation correction
3. Target-system configuration correction
4. Migration-script correction
""",

    "preprod": """
**Pre-Production / Pre-Prod**

A non-production environment used to validate migrated data before
production.

Typical validation:
- Record counts
- Field mapping
- Amount reconciliation
- Frontend display
- Loan status
- Repayment schedule
- Charges
- Receipts
- Documents
- Accounting
""",

    "production": """
**Production / Prod**

The live target LMS environment used by actual users/business operations.

Production migration requires stronger controls because changes affect
live financial data.
""",

    # --------------------------------------------------------
    # DOCUMENTS
    # --------------------------------------------------------

    "document_migration": """
**Document Migration**

Migration of borrower/loan documents from the legacy system to the
target LMS.

Documents may be stored in:
- S3/object storage
- Local storage
- Document management system
- Legacy LMS repository

Common document mapping:
- Customer
- Loan
- Document type
- Document name
- File path/key
- Upload date
- Document status

For cloud storage, access may require:
- Bucket
- Prefix/path
- Read/list permissions
- Credentials/role
- Region
""",
}


# ============================================================
# 2. ALIASES / SYNONYMS
# ============================================================

FINTECH_ALIASES: Dict[str, str] = {

    # LMS
    "loan management system": "lms",
    "loan mgmt system": "lms",
    "loan management": "lms",

    # LOS
    "loan origination system": "los",
    "origination system": "los",

    # Repayment
    "repayment": "repayment_schedule",
    "repayment schedule": "repayment_schedule",
    "repayment data": "repayment_schedule",
    "rps": "repayment_schedule",
    "schedule": "repayment_schedule",
    "emi schedule": "repayment_schedule",

    # Foreclosure
    "fc": "foreclosure",
    "preclosure": "foreclosure",
    "pre-closure": "foreclosure",
    "foreclose": "foreclosure",
    "foreclosure": "foreclosure",

    # Part payment
    "pp": "part_payment",
    "part payment": "part_payment",
    "part-payment": "part_payment",
    "partpay": "part_payment",

    # DPD
    "days past due": "dpd",
    "days overdue": "dpd",

    # NPA
    "non performing asset": "npa",
    "non-performing asset": "npa",

    # NACH
    "national automated clearing house": "nach",
    "mandate": "nach",
    "nach mandate": "nach",
    "e nach": "enach",
    "e-nach": "enach",

    # Banking
    "unique mandate reference number": "umrn",
    "mandate reference": "umrn",

    # Collateral
    "loan to value": "ltv",
    "loan-to-value": "ltv",

    # Underwriting
    "fixed obligation to income ratio": "foir",
    "fixed obligations to income ratio": "foir",

    # Customer
    "borrower": "customer",
    "applicant": "applicant",
    "co borrower": "coapplicant",
    "co-borrower": "coapplicant",
    "co applicant": "coapplicant",
    "co-applicant": "coapplicant",

    # Charges
    "processing charges": "processing_fee",
    "processing charge": "processing_fee",
    "processing fees": "processing_fee",
    "processing fee": "processing_fee",

    # Excess
    "excess": "excess_money",
    "excess amount": "excess_money",
    "excess money": "excess_money",
    "overpayment": "excess_money",

    # Status
    "fully paid": "paid",
    "payment done": "paid",
    "unpaid": "pending",
    "due": "outstanding",

    # Migration
    "data migration": "migration",
    "data migrate": "migration",
    "re migrate": "remigration",
    "re-migrate": "remigration",
    "re-migration": "remigration",

    # Accounting
    "general ledger": "gl",
    "ledger": "gl",

    # Co-lending
    "co lending": "colending",
    "co-lender": "colending",
    "co lender": "colending",
}


# ============================================================
# 3. FIELD MEANING KNOWLEDGE
# ============================================================

FIELD_DICTIONARY: Dict[str, str] = {

    "loan_id": "Unique identifier of the loan account.",
    "loan_application_number": "Unique identifier of the loan application.",
    "customer_id": "Identifier of the customer/party.",
    "repayment_schedule_id": "Identifier of a repayment schedule record.",
    "due_date": "Contractual date on which the installment becomes due.",
    "installment_amount": "Total scheduled installment amount.",
    "principal": "Principal component of the installment.",
    "interest": "Interest component of the installment.",
    "opening_balance": "Balance at the beginning of the schedule period.",
    "closing_balance": "Balance after relevant repayment/adjustment.",
    "principal_outstanding": "Remaining principal amount.",
    "interest_rate": "Contractual interest rate.",
    "effective_rate": "Effective annualized/periodic rate as configured.",
    "received_amount": "Amount received/allocated.",
    "principal_due": "Unpaid principal component.",
    "interest_due": "Unpaid interest component.",
    "pending_amount": "Remaining payable amount.",
    "status": "Current state of the record/transaction.",
    "asset_classification": "Classification such as regular/substandard/doubtful/loss.",
    "branch": "Organizational/location unit servicing the loan.",
    "product": "Broad loan product category.",
    "scheme": "Specific loan scheme/configuration.",
    "sanction_amount": "Amount approved/sanctioned.",
    "disbursed_amount": "Amount disbursed.",
    "net_disbursed_amount": "Amount released after applicable deductions.",
    "charge_amount": "Base charge amount.",
    "gst_amount": "Applicable GST amount.",
    "total_charge": "Charge including applicable taxes.",
    "umrn": "Unique mandate reference number.",
    "mandate_amount": "Maximum/registered mandate amount.",
    "ifsc": "Indian Financial System Code identifying a bank branch.",
    "account_number": "Bank account number.",
    "valuation_amount": "Value assigned to collateral.",
    "ltv": "Loan-to-value ratio.",
    "foir": "Fixed obligations to income ratio.",
}


# ============================================================
# 4. REPAYMENT STATUS KNOWLEDGE
# ============================================================

REPAYMENT_STATUS_RULES: Dict[str, str] = {

    "paid": """
Paid installment:
- Installment obligation has been satisfied.
- Principal due should generally be 0.
- Interest due should generally be 0.
- Pending amount should generally be 0.
- Received amount may equal the amount allocated to the installment.
""",

    "pending": """
Pending installment:
- Some amount remains unpaid.
- Principal/interest due may remain.
- Pending amount may be greater than 0.
- Received amount may be 0 or partially populated.
""",

    "outstanding": """
Outstanding installment:
- An amount remains payable.
- It may represent principal, interest, total installment,
  or another outstanding component depending on the field.
""",

    "foreclosure": """
Foreclosure:
- Represents final settlement/closure.
- Final relevant balance should generally be 0.
- Future active installments should not remain after foreclosure.
""",

    "part_payment": """
Part-payment:
- Special principal reduction transaction.
- Should not automatically be treated as a normal EMI.
- May have special installment/status representation.
""",
}


# ============================================================
# 5. COMMON MIGRATION VALIDATIONS
# ============================================================

MIGRATION_VALIDATIONS: Dict[str, str] = {

    "loan_id_consistency": """
Check whether the same loan_id is consistently mapped across all
loan-level sheets.

Example:
Customer
Loan Application
Collateral
Disbursement
Repayment
Charges
Payments
Receipts
Excess Money
""",

    "repayment_installment_check": """
For normal EMI rows:

principal + interest should generally reconcile with
installment_amount, subject to:
- Rounding
- Taxes
- Other components
- Special transactions
- Part-payment
- Foreclosure
- Adjustments

Do not blindly apply this check to special transaction rows.
""",

    "paid_installment_check": """
For paid rows, investigate whether:
- principal_due != 0
- interest_due != 0
- pending_amount != 0

Such values may indicate incomplete allocation or incorrect migration,
subject to the target LMS design.
""",

    "closing_balance_check": """
For closed/foreclosed loans:
- Identify the final relevant schedule row.
- Check whether closing balance is zero.
- If not zero, investigate repayment allocation,
  foreclosure adjustment, excess money, or missing transaction data.
""",

    "future_installment_check": """
For a foreclosed loan:
- Identify foreclosure date.
- Check whether active installments exist after foreclosure.
- Future rows may require cancellation/closure according to target LMS
  behavior.
""",

    "negative_pending_check": """
Negative pending amount generally indicates that received/adjusted amount
exceeds the amount considered due.

Possible causes:
- Overpayment
- Advance payment
- Incorrect allocation
- Excess money
- Missing refund
- Incorrect source data

Do not simply convert a negative amount to zero without understanding
where the excess should go.
""",

    "duplicate_umrn_check": """
Check duplicate UMRN values.

A duplicate UMRN should be investigated for:
- Same customer
- Same bank account
- Same mandate
- Multiple loans
- Reused/incorrect mandate
- Source system behavior

Do not automatically declare every duplicate invalid.
""",

    "branch_validation": """
Validate branch names/codes against target Production configuration.

Possible issue types:
- Branch does not exist
- Branch exists but inactive
- Name mismatch
- Code mismatch
- Missing branch code
- Legacy branch not configured in target system
""",

    "scheme_validation": """
Validate source scheme codes against target Production scheme codes.

Do not assume that the source scheme name/code is valid in the target.
Use the target master/configuration mapping.
""",

    "charge_validation": """
Validate:
- Charge type
- Charge amount
- GST
- Total amount
- Charge applicability
- Target configuration
- Receipt mapping
- Disbursal deduction mapping

Do not create or invent a charge type that does not exist in the target
system unless explicitly configured.
""",

    "disbursement_reconciliation": """
Conceptually reconcile:

Gross Disbursement
- Adjusted Deductions
- Applicable Adjustments
= Net Disbursed

The exact formula must follow target LMS configuration.
""",

    "customer_validation": """
Check:
- customer_id mapping
- Name
- PAN
- Aadhaar/other KYC
- Date of birth
- Gender where applicable
- Address
- Customer roles
- Duplicate identifiers

Do not automatically merge duplicate customers without business confirmation.
""",

    "collateral_validation": """
Check:
- Collateral type
- Ownership
- Valuation
- Valuation date
- Property/asset details
- Registration details
- Required fields
- Loan mapping
- LTV consistency
""",
}


# ============================================================
# 6. DOMAIN RELATIONSHIPS
# ============================================================

DOMAIN_RELATIONSHIPS: Dict[str, List[str]] = {

    "loan": [
        "customer",
        "loan_application",
        "product",
        "scheme",
        "branch",
        "collateral",
        "disbursement",
        "repayment_schedule",
        "payments",
        "receipts",
        "charges",
        "bank_details",
        "nach",
        "excess_money",
    ],

    "repayment_schedule": [
        "loan",
        "emi",
        "principal",
        "interest",
        "opening_balance",
        "closing_balance",
        "received_amount",
        "principal_due",
        "interest_due",
        "pending_amount",
        "dpd",
    ],

    "foreclosure": [
        "loan",
        "repayment_schedule",
        "principal",
        "interest",
        "foreclosure_charge",
        "excess_money",
        "refund",
        "closure",
    ],

    "part_payment": [
        "loan",
        "principal",
        "principal_outstanding",
        "repayment_schedule",
        "emi",
        "tenure",
    ],

    "nach": [
        "customer",
        "loan",
        "bank_details",
        "umrn",
        "mandate_amount",
    ],

    "collateral": [
        "loan",
        "valuation",
        "ltv",
        "mortgage",
        "hypothecation",
    ],

    "charges": [
        "loan",
        "processing_fee",
        "gst",
        "receipt",
        "disbursement",
    ],
}


# ============================================================
# 7. COMMON MIGRATION SCENARIOS
# ============================================================

MIGRATION_SCENARIOS: Dict[str, str] = {

    "closed_loan_non_zero_balance": """
Scenario:
Loan status = Closed
Final repayment closing balance != 0

Possible investigation areas:
1. Missing repayment row
2. Incorrect principal allocation
3. Incorrect interest allocation
4. Foreclosure amount missing
5. Charge/adjustment not considered
6. Excess money not handled
7. Incorrect source data
8. Incorrect migration transformation

Do not directly change the value to zero without understanding the source
transaction flow.
""",

    "paid_row_has_due": """
Scenario:
Status = Paid
but principal_due or interest_due is populated.

Likely investigation:
- Payment allocation
- Receipt mapping
- Source data
- Migration transformation
- Reversal/adjustment
- Target system behavior
""",

    "negative_pending": """
Scenario:
pending_amount < 0

Interpretation:
The amount allocated/received may exceed the amount currently considered
due.

Possible handling:
- Excess Money
- Advance EMI
- Refund
- IRR refund
- Allocation correction

Do not blindly replace with zero.
""",

    "installment_mismatch": """
Scenario:
principal + interest != installment_amount

First classify the row:
- Normal EMI
- Part-payment
- Foreclosure
- Adjustment
- Fee
- Moratorium
- Special transaction

Only normal EMI rows should generally be tested using the simple
principal + interest reconciliation.
""",

    "duplicate_customer_identifier": """
Scenario:
Same PAN/Aadhaar appears against multiple customer IDs.

Possible explanations:
- Duplicate customer creation
- Multiple legitimate loan relationships
- Top-up
- Existing customer mapped incorrectly
- Source system duplication

Requires business validation before merging.
""",

    "duplicate_nach": """
Scenario:
Same UMRN appears for multiple loans/customers.

Investigate:
- Same borrower?
- Same bank account?
- Same mandate?
- Same lender mandate?
- Source reuse?
- Migration duplication?

Do not automatically delete duplicates.
""",

    "missing_branch": """
Scenario:
Source branch is not available in target Production.

Possible solution:
- Add/configure branch in target
- Map legacy branch to existing target branch
- Obtain client confirmation
- Update migration mapping

Do not randomly substitute another branch.
""",

    "missing_charge_master": """
Scenario:
Source contains a charge but target Production does not have the
corresponding charge configuration.

Required action:
- Confirm charge master/configuration
- Create/map charge in target if approved
- Then migrate charge data

Do not silently skip financial charges.
""",
}


# ============================================================
# 8. TERMINOLOGY NORMALIZATION
# ============================================================

def normalize_query(query: str) -> str:
    """
    Normalize user query for better concept matching.
    """

    q = query.lower().strip()

    replacements = {
        "-": " ",
        "_": " ",
        "/": " ",
    }

    for old, new in replacements.items():
        q = q.replace(old, new)

    return " ".join(q.split())


def resolve_alias(query: str) -> Optional[str]:
    """
    Resolve common fintech aliases/synonyms to canonical concept keys.
    """

    q = normalize_query(query)

    # Exact alias match first
    if q in FINTECH_ALIASES:
        return FINTECH_ALIASES[q]

    # Exact dictionary key
    if q in FINTECH_DICTIONARY:
        return q

    # Search aliases inside longer queries
    for alias, key in sorted(
        FINTECH_ALIASES.items(),
        key=lambda x: len(x[0]),
        reverse=True,
    ):
        if alias in q:
            return key

    # Search canonical concepts
    for key in FINTECH_DICTIONARY:
        if key.replace("_", " ") in q:
            return key

    return None


# ============================================================
# 9. FIELD LOOKUP
# ============================================================

def lookup_field(field_name: str) -> Optional[str]:
    """
    Return explanation of a migration/LMS field.
    """

    field = field_name.lower().strip()

    field = field.replace("-", "_").replace(" ", "_")

    return FIELD_DICTIONARY.get(field)


# ============================================================
# 10. CONCEPT LOOKUP
# ============================================================

def lookup_fintech_concept(query: str) -> Optional[str]:
    """
    Find the most relevant fintech/LMS concept for a user query.

    Supports:
    - Exact concept
    - Alias
    - Synonym
    - Embedded terminology
    """

    if not query:
        return None

    key = resolve_alias(query)

    if key:
        return FINTECH_DICTIONARY.get(key)

    return None


# ============================================================
# 11. MULTI-CONCEPT LOOKUP
# ============================================================

def find_fintech_concepts(query: str) -> List[Tuple[str, str]]:
    """
    Find all recognized fintech concepts present in the query.

    Useful for queries such as:

    "closed loan ka closing balance 0 kyu hona chahiye"

    This may identify:
    - closed
    - loan
    - closing_balance
    """

    q = normalize_query(query)

    found = []

    # Canonical concepts
    for key, explanation in FINTECH_DICTIONARY.items():

        variants = {
            key,
            key.replace("_", " "),
        }

        if any(v in q for v in variants):
            found.append((key, explanation))

    # Aliases
    for alias, key in FINTECH_ALIASES.items():

        if alias in q:
            explanation = FINTECH_DICTIONARY.get(key)

            if explanation:
                found.append((key, explanation))

    # Remove duplicates while preserving order
    result = []
    seen = set()

    for key, explanation in found:
        if key not in seen:
            seen.add(key)
            result.append((key, explanation))

    return result


# ============================================================
# 12. GET VALIDATION RULE
# ============================================================

def get_validation_rule(rule_name: str) -> Optional[str]:
    """
    Return a predefined migration validation rule.
    """

    rule = normalize_query(rule_name)

    rule = rule.replace(" ", "_")

    return MIGRATION_VALIDATIONS.get(rule)


# ============================================================
# 13. GET SCENARIO
# ============================================================

def get_migration_scenario(scenario: str) -> Optional[str]:
    """
    Return domain guidance for a known migration scenario.
    """

    scenario = normalize_query(scenario)
    scenario = scenario.replace(" ", "_")

    return MIGRATION_SCENARIOS.get(scenario)


# ============================================================
# 14. DOMAIN RELATIONSHIP LOOKUP
# ============================================================

def get_related_concepts(concept: str) -> List[str]:
    """
    Return related LMS/fintech concepts.
    """

    key = resolve_alias(concept)

    if not key:
        key = concept.lower().strip()

    return DOMAIN_RELATIONSHIPS.get(key, [])


# ============================================================
# 15. SMART DOMAIN SEARCH
# ============================================================

def search_domain_knowledge(query: str) -> Dict:
    """
    Central knowledge search function for the AI assistant.

    Returns:
    - Primary concept
    - Explanation
    - Related concepts
    - Matching fields
    - Matching validations
    """

    q = normalize_query(query)

    primary_key = resolve_alias(q)

    result = {
        "primary_concept": primary_key,
        "explanation": None,
        "related_concepts": [],
        "fields": [],
        "validations": [],
    }

    # Primary concept
    if primary_key:
        result["explanation"] = FINTECH_DICTIONARY.get(primary_key)
        result["related_concepts"] = get_related_concepts(primary_key)

    # Field matching
    for field, explanation in FIELD_DICTIONARY.items():

        field_variants = [
            field,
            field.replace("_", " "),
        ]

        if any(v in q for v in field_variants):
            result["fields"].append({
                "field": field,
                "meaning": explanation,
            })

    # Validation matching
    validation_keywords = {
        "closing balance": "closing_balance_check",
        "paid": "paid_installment_check",
        "negative pending": "negative_pending_check",
        "pending amount": "negative_pending_check",
        "umrn": "duplicate_umrn_check",
        "branch": "branch_validation",
        "scheme": "scheme_validation",
        "charge": "charge_validation",
        "disbursement": "disbursement_reconciliation",
        "customer": "customer_validation",
        "collateral": "collateral_validation",
    }

    for keyword, validation_key in validation_keywords.items():

        if keyword in q:
            rule = MIGRATION_VALIDATIONS.get(validation_key)

            if rule:
                result["validations"].append({
                    "rule": validation_key,
                    "explanation": rule,
                })

    return result


# ============================================================
# 16. SIMPLE API FOR ASSISTANT
# ============================================================

def ask_fintech_kb(query: str) -> str:
    """
    Simple function for connecting this KB to an AI assistant.

    Example:

        answer = ask_fintech_kb(
            "paid repayment row me principal due kya hona chahiye?"
        )
    """

    result = search_domain_knowledge(query)

    parts = []

    if result["explanation"]:
        parts.append(result["explanation"])

    if result["fields"]:
        parts.append("\n**Relevant Fields:**")

        for item in result["fields"]:
            parts.append(
                f"- `{item['field']}`: {item['meaning']}"
            )

    if result["validations"]:
        parts.append("\n**Relevant Validation Guidance:**")

        for item in result["validations"]:
            parts.append(
                f"- {item['explanation']}"
            )

    if result["related_concepts"]:
        parts.append(
            "\n**Related Concepts:** "
            + ", ".join(result["related_concepts"])
        )

    if not parts:
        return (
            "No specific fintech concept was found in the knowledge base. "
            "Use the general assistant/LLM reasoning for this query."
        )

    return "\n".join(parts)