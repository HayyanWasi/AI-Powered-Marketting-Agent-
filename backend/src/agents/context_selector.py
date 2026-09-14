from src.agents.context import ContentSlot, GuestData


class ContextSelector:
    """Deterministically selects contextually relevant facts for content generation."""

    @staticmethod
    def select_guest_context(slot: ContentSlot, guests: tuple[GuestData, ...]) -> str:
        """Selects relevant guest context based on the content slot theme."""
        if not guests:
            return ""

        selected_facts = []
        for g in guests:
            # We don't inject the full biography.
            # We provide their title, organization, and a relevant fact based on the slot's theme.
            base_info = f"{g.full_name}"
            if g.position or g.organization:
                org = g.organization or "independent"
                pos = g.position or "Professional"
                base_info += f" ({pos} at {org})"

            # If they have expertise, include it
            expertise_str = f" Expertise: {', '.join(g.expertise)}." if g.expertise else ""

            # Selectively use first sentence of bio as a teaser
            bio_teaser = ""
            if g.biography:
                first_sentence = g.biography.split(".")[0] + "."
                bio_teaser = f" Background: {first_sentence}"

            selected_facts.append(f"- {base_info}.{expertise_str}{bio_teaser}")

        return "\n".join(selected_facts)
