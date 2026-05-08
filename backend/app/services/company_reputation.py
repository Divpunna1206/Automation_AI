KNOWN_COMPANY_REPUTATION = {
    "openai": 95,
    "microsoft": 92,
    "google": 94,
    "meta": 90,
    "amazon": 88,
    "anthropic": 93,
    "acme ai": 72,
}


class CompanyReputationService:
    def score(self, company: str) -> int:
        return KNOWN_COMPANY_REPUTATION.get(company.lower(), 60)
