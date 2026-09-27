# A sealed bag carries its own parts

Date: 2026-09-27. Audit 2026-09-27, item B-17.

## The finding

A day compiled in several parts is archived as an `archive-manifest/v2` bag.
The manifest records each part's byte range and the receipt for its digest.
The reader did not trust that record. It cut the payload again with today's
rule (`_daily_part_bounds`, `MAX_DAILY_PART_BYTES`) and refused the bag unless
the two cuts agreed (`evidence_resolver._part_receipts`). A quote from a part
was found the same way (`_referenced_source` → `compile_part_slice`). If the rule
ever changed, every v2 bag sealed under the old rule would stop validating, and
every page quoting it would lose its evidence. The bag was sealed; the rule it
was checked against was not.

## Sources (fetched 2026-09-27)

1. RFC 8493, The BagIt File Packaging Format —
   https://www.rfc-editor.org/rfc/rfc8493.html. A bag is valid when "every
   checksum in every payload manifest and tag manifest has been successfully
   verified against the contents of the corresponding file"; processing a bag
   "does not require any understanding of the payload file contents". The
   bag's own record is the authority, not the software that made it.
2. Digital Preservation Coalition, Digital Preservation Handbook, "Fixity and
   checksums" — https://www.dpconline.org/handbook/technical-solutions-and-tools/fixity-and-checksums.
   Verification computes a new checksum and compares it "with the reference
   value that is known to be correct", a value stored "within a 'manifest'
   that accompanies the files".
3. OAIS (ISO 14721 / CCSDS 650.0-M-2), summarised at
   https://en.wikipedia.org/wiki/Open_Archival_Information_System (the CCSDS PDF
   was fetched but could not be converted to text on this machine, so the
   primary wording was not read). An archival package carries the
   Preservation Description Information — checksums, provenance — needed to
   preserve its content, together with the content.

All three say the same thing: what an archived object is checked against
travels with the object and is recorded when it is sealed.

## Alternatives

- Keep recomputing, and freeze `MAX_DAILY_PART_BYTES` forever. It turns a
  tuning constant into a hidden format version; rejected.
- Record a rule version in the manifest and keep every past rule in code.
  Needs a schema change and keeps dead code alive; rejected while the parts
  themselves are already recorded.
- **Chosen:** trust the recorded parts, and check what makes them a correct
  record without any size rule: they cover the payload from its first byte
  to its last with no gap or overlap, every cut sits where an entry begins,
  and each part's digest is the one its receipt names (already checked). A
  quote is looked for at the recorded part starts, the same search
  `compile_part_slice` makes over today's starts for a live day.

## Trade-offs

A bag with a forged part table still has to present a receipt for each part's
digest, so trusting the table admits nothing a receipt did not already
vouch for. The live day is still cut by today's rule, because it is compiled
by today's rule.
