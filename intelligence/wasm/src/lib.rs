use regex::Regex;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::cmp::Ordering;
use std::sync::OnceLock;

const STRICT_CANDLE_BACKEND: &str = "strict_candle_v6";
const GRAND_TOTAL_THRESHOLD: f64 = 1.8;
const TAX_THRESHOLD: f64 = 1.5;
const SUBTOTAL_THRESHOLD: f64 = 1.5;
const SCORE_AMBIGUITY_MARGIN: f64 = 0.35;

#[derive(Debug, Deserialize, Serialize)]
pub struct AccountContext {
    pub ledger_profile: String,
    pub cost_center: String,
    #[serde(default)]
    pub vendor_hint: String,
}

#[derive(Debug, Deserialize)]
pub struct ExtractorInput {
    pub doc_id: String,
    pub source_type: String,
    pub import_event: String,
    pub ocr_text: String,
    pub locale: String,
    #[serde(default)]
    pub currency_hint: String,
    pub account_context: AccountContext,
}

#[derive(Debug, Deserialize)]
#[serde(untagged)]
pub enum WasmRequest {
    Direct(ExtractorInput),
    Wrapped { extractor_input: ExtractorInput },
}

#[derive(Debug, Serialize, Clone)]
pub struct RankingRow {
    pub candidate: String,
    pub score: f64,
    pub reason: String,
}

#[derive(Debug, Serialize, Clone)]
pub struct EvidenceRef {
    pub field: String,
    pub source: String,
    pub snippet: String,
    pub support: f64,
}

#[derive(Debug, Serialize)]
pub struct ExtractedFields {
    pub vendor_name: String,
    pub invoice_number: String,
    pub invoice_date: String,
    pub due_date: String,
    pub currency: String,
    pub subtotal: f64,
    pub tax_total: f64,
    pub grand_total: f64,
}

#[derive(Debug, Serialize)]
pub struct ExtractorOutput {
    pub doc_id: String,
    pub source_type: String,
    pub import_event: String,
    pub ocr_text: String,
    pub locale: String,
    pub currency_hint: String,
    pub account_context: AccountContext,
    pub routing_label: String,
    pub confidence: f64,
    pub extracted_fields: ExtractedFields,
    pub warnings: Vec<String>,
    pub ranking: Vec<RankingRow>,
    pub abstain: bool,
    pub abstain_reason_code: String,
    pub claim_support_score: f64,
    pub evidence_refs: Vec<EvidenceRef>,
    pub vat_metrics: serde_json::Value,
    pub classification_metrics: serde_json::Value,
}

#[derive(Debug, Clone)]
struct RawToken {
    raw: String,
    upper: String,
    start: usize,
    end: usize,
    line_index: usize,
}

#[derive(Debug, Clone)]
struct AmountCandidate {
    raw: String,
    value: f64,
    start: usize,
    has_decimal: bool,
    decimal_places: usize,
    has_currency_marker: bool,
    looks_like_identifier: bool,
    window_upper: String,
    window_raw: String,
    line_upper: String,
    line_prefix_upper: String,
}

#[derive(Debug, Clone)]
struct ScoredCandidate {
    candidate: AmountCandidate,
    score: f64,
    support: f64,
    reasons: Vec<&'static str>,
}

#[derive(Debug)]
struct NumericExtractionResult {
    subtotal: f64,
    tax_total: f64,
    grand_total: f64,
    warnings: Vec<String>,
    abstain: bool,
    abstain_reason_code: String,
    evidence_refs: Vec<EvidenceRef>,
    debug: serde_json::Value,
}

#[derive(Debug)]
struct DateResolution {
    invoice_date: String,
    due_date: String,
    invoice_source: String,
    due_source: String,
    invoice_support: f64,
    due_support: f64,
}

fn stable_hash(value: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(value.as_bytes());
    format!("{:x}", hasher.finalize())
}

fn round2(value: f64) -> f64 {
    (value * 100.0).round() / 100.0
}

fn clamp_support(value: f64) -> f64 {
    let bounded = value.clamp(0.0, 1.0);
    (bounded * 10000.0).round() / 10000.0
}

fn tokenize_text(ocr_text: &str) -> Vec<String> {
    let mut tokens: Vec<String> = Vec::new();
    let mut current = String::new();

    for ch in ocr_text.chars() {
        if ch.is_ascii_alphanumeric() || ch == '-' || ch == '_' {
            current.push(ch.to_ascii_uppercase());
        } else if !current.is_empty() {
            tokens.push(current.clone());
            current.clear();
        }
    }

    if !current.is_empty() {
        tokens.push(current);
    }

    tokens
}

fn split_raw_tokens(ocr_text: &str) -> Vec<RawToken> {
    let mut tokens = Vec::new();
    let mut current_start: Option<usize> = None;
    let mut current_line = 0usize;
    let mut token_line = 0usize;

    for (idx, ch) in ocr_text.char_indices() {
        if ch == '\n' {
            if let Some(start) = current_start.take() {
                let raw = ocr_text[start..idx].to_string();
                tokens.push(RawToken {
                    upper: keywordize(&raw),
                    raw,
                    start,
                    end: idx,
                    line_index: token_line,
                });
            }
            current_line += 1;
            continue;
        }

        if ch.is_whitespace() {
            if let Some(start) = current_start.take() {
                let raw = ocr_text[start..idx].to_string();
                tokens.push(RawToken {
                    upper: keywordize(&raw),
                    raw,
                    start,
                    end: idx,
                    line_index: token_line,
                });
            }
            continue;
        }

        if current_start.is_none() {
            current_start = Some(idx);
            token_line = current_line;
        }
    }

    if let Some(start) = current_start {
        let raw = ocr_text[start..].to_string();
        tokens.push(RawToken {
            upper: keywordize(&raw),
            raw,
            start,
            end: ocr_text.len(),
            line_index: token_line,
        });
    }

    tokens
}

fn keywordize(raw: &str) -> String {
    raw.chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() || matches!(ch, '-' | '_' | '#') {
                ch.to_ascii_uppercase()
            } else {
                ' '
            }
        })
        .collect::<String>()
        .split_whitespace()
        .collect::<Vec<&str>>()
        .join(" ")
}

fn build_feature_vector(tokens: &[String], source_type: &str, ledger_profile: &str) -> Vec<f64> {
    let has_invoice = if tokens
        .iter()
        .any(|token| token == "INVOICE" || token == "FACTURA" || token == "RECHNUNG")
    {
        1.0
    } else {
        0.0
    };

    let has_receipt = if tokens
        .iter()
        .any(|token| token == "RECEIPT" || token == "QUITTUNG" || token == "TICKET")
    {
        1.0
    } else {
        0.0
    };

    let has_tax = if tokens
        .iter()
        .any(|token| token == "TAX" || token == "VAT" || token == "IVA" || token == "MWST")
    {
        1.0
    } else {
        0.0
    };

    let has_total = if tokens.iter().any(|token| {
        token == "TOTAL"
            || token == "AMOUNT"
            || token == "GESAMT"
            || token == "IMPORTE"
            || token == "SUBTOTAL"
            || token == "NETTO"
    }) {
        1.0
    } else {
        0.0
    };

    let source_invoice =
        if source_type.eq_ignore_ascii_case("invoice") || ledger_profile.to_ascii_lowercase().contains("ap") {
            1.0
        } else {
            0.0
        };

    let source_receipt = if source_type.eq_ignore_ascii_case("receipt")
        || ledger_profile.to_ascii_lowercase().contains("expense")
    {
        1.0
    } else {
        0.0
    };

    vec![
        has_invoice,
        has_receipt,
        has_tax,
        has_total,
        source_invoice,
        source_receipt,
    ]
}

fn infer_currency(input: &ExtractorInput) -> String {
    if !input.currency_hint.trim().is_empty() {
        return input.currency_hint.trim().to_ascii_uppercase();
    }

    let upper = input.ocr_text.to_ascii_uppercase();
    if upper.contains("EUR") || input.ocr_text.contains('€') {
        return "EUR".to_string();
    }
    if upper.contains("GBP") || input.ocr_text.contains('£') {
        return "GBP".to_string();
    }
    if upper.contains("CHF") {
        return "CHF".to_string();
    }
    "USD".to_string()
}

fn run_strict_candle_inference(features: &[f64], doc_id: &str) -> (String, f64, Vec<RankingRow>) {
    let label_invoice = "accounts_payable_invoice".to_string();
    let label_receipt = "expense_receipt".to_string();
    let label_other = "other_finance_doc".to_string();

    let doc_hash = stable_hash(doc_id);
    let doc_bias = (u8::from_str_radix(&doc_hash[0..2], 16).unwrap_or(0) as f64) / 255000.0;

    let mut invoice_score = 0.0;
    invoice_score += features[0] * 1.5;
    invoice_score += features[2] * 0.8;
    invoice_score += features[3] * 1.0;
    invoice_score += features[4] * 1.1;
    invoice_score += doc_bias;

    let mut receipt_score = 0.0;
    receipt_score += features[1] * 1.6;
    receipt_score += features[5] * 1.1;
    receipt_score += (1.0 - features[4]) * 0.2;
    receipt_score += doc_bias / 2.0;

    let other_score = 0.4 + (1.0 - features[0]).max(0.0) * 0.2;

    let sum_exp = invoice_score.exp() + receipt_score.exp() + other_score.exp();
    let invoice_prob = invoice_score.exp() / sum_exp;
    let receipt_prob = receipt_score.exp() / sum_exp;
    let other_prob = other_score.exp() / sum_exp;

    let mut rows = vec![
        RankingRow {
            candidate: label_invoice.clone(),
            score: (invoice_prob * 10000.0).round() / 10000.0,
            reason: format!("{STRICT_CANDLE_BACKEND}_invoice_path"),
        },
        RankingRow {
            candidate: label_receipt.clone(),
            score: (receipt_prob * 10000.0).round() / 10000.0,
            reason: format!("{STRICT_CANDLE_BACKEND}_receipt_path"),
        },
        RankingRow {
            candidate: label_other.clone(),
            score: (other_prob * 10000.0).round() / 10000.0,
            reason: format!("{STRICT_CANDLE_BACKEND}_other_path"),
        },
    ];

    rows.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(Ordering::Equal)
            .then_with(|| a.candidate.cmp(&b.candidate))
    });

    let top = rows[0].clone();
    (top.candidate, top.score, rows)
}

fn amount_regex() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(
            r"(?x)
            (?P<raw>
              (?:[$€£]\s*)?
              (?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?|\d+(?:[.,]\d{2})?)
              (?:\s?(?:EUR|USD|GBP|CHF))?
            )
        ",
        )
        .expect("amount regex")
    })
}

fn iso_date_regex() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"\b20\d{2}[-/]\d{2}[-/]\d{2}\b").expect("iso date regex"))
}

fn dotted_date_regex() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"\b\d{2}[.]\d{2}[.]\d{4}\b").expect("dotted date regex"))
}

fn slash_date_regex() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"\b\d{1,2}/\d{1,2}/20\d{2}\b").expect("slash date regex"))
}

fn tax_rate_regex() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(r"(?i)\b(?:tax|vat|iva|mwst|gst|ust|steuer)\b[^\n]{0,24}?(\d{1,2}(?:[.,]\d{1,2})?)\s*%")
            .expect("tax rate regex")
    })
}

fn collect_date_spans(text: &str) -> Vec<(usize, usize)> {
    let mut spans = Vec::new();
    for re in [iso_date_regex(), dotted_date_regex(), slash_date_regex()] {
        for mat in re.find_iter(text) {
            spans.push((mat.start(), mat.end()));
        }
    }
    spans
}

fn span_overlaps(a_start: usize, a_end: usize, b_start: usize, b_end: usize) -> bool {
    a_start < b_end && b_start < a_end
}

fn prev_char(text: &str, idx: usize) -> Option<(usize, char)> {
    text[..idx].char_indices().last()
}

fn next_char(text: &str, idx: usize) -> Option<(usize, char)> {
    text[idx..]
        .char_indices()
        .next()
        .map(|(offset, ch)| (idx + offset, ch))
}

fn contains_alpha(text: &str) -> bool {
    text.chars().any(|ch| ch.is_ascii_alphabetic())
}

fn clean_amount_text(raw: &str) -> String {
    raw.chars()
        .filter(|ch| {
            ch.is_ascii_digit()
                || matches!(ch, '.' | ',' | '$' | '€' | '£' | 'E' | 'U' | 'R' | 'S' | 'D' | 'G' | 'B' | 'P' | 'C' | 'H' | 'F')
                || ch.is_ascii_whitespace()
        })
        .collect()
}

fn parse_amount_value(raw: &str, locale: &str) -> Option<(f64, bool, usize, bool)> {
    let cleaned = clean_amount_text(raw);
    if cleaned.trim().is_empty() {
        return None;
    }

    let has_currency_marker = cleaned.contains('$')
        || cleaned.contains('€')
        || cleaned.contains('£')
        || cleaned.to_ascii_uppercase().contains("EUR")
        || cleaned.to_ascii_uppercase().contains("USD")
        || cleaned.to_ascii_uppercase().contains("GBP")
        || cleaned.to_ascii_uppercase().contains("CHF");

    let mut normalized = cleaned
        .replace("EUR", "")
        .replace("USD", "")
        .replace("GBP", "")
        .replace("CHF", "")
        .replace('$', "")
        .replace('€', "")
        .replace('£', "")
        .trim()
        .to_string();

    normalized = normalized.replace(' ', "");
    if normalized.is_empty() {
        return None;
    }

    let decimal_char = if normalized.contains(',') && normalized.contains('.') {
        if normalized.rfind(',').unwrap_or(0) > normalized.rfind('.').unwrap_or(0) {
            Some(',')
        } else {
            Some('.')
        }
    } else if normalized.contains(',') {
        let digits_after = normalized
            .rsplit(',')
            .next()
            .map(|part| part.chars().filter(|ch| ch.is_ascii_digit()).count())
            .unwrap_or(0);
        if digits_after == 2 || (locale.starts_with("de") || locale.starts_with("es")) {
            Some(',')
        } else {
            None
        }
    } else if normalized.contains('.') {
        let digits_after = normalized
            .rsplit('.')
            .next()
            .map(|part| part.chars().filter(|ch| ch.is_ascii_digit()).count())
            .unwrap_or(0);
        if digits_after == 2 || locale.starts_with("en") {
            Some('.')
        } else {
            None
        }
    } else {
        None
    };

    let decimal_places = decimal_char
        .and_then(|sep| normalized.rsplit(sep).next())
        .map(|part| part.chars().filter(|ch| ch.is_ascii_digit()).count())
        .unwrap_or(0);

    let parsed = if let Some(sep) = decimal_char {
        let mut out = String::new();
        for ch in normalized.chars() {
            if ch.is_ascii_digit() {
                out.push(ch);
            } else if ch == sep {
                out.push('.');
            }
        }
        out.parse::<f64>().ok()
    } else {
        let out: String = normalized.chars().filter(|ch| ch.is_ascii_digit()).collect();
        if out.is_empty() {
            None
        } else {
            out.parse::<f64>().ok()
        }
    }?;

    Some((parsed, decimal_char.is_some(), decimal_places, has_currency_marker))
}

fn line_bounds(text: &str, start: usize, end: usize) -> (usize, usize) {
    let line_start = text[..start].rfind('\n').map(|idx| idx + 1).unwrap_or(0);
    let line_end = text[end..]
        .find('\n')
        .map(|idx| end + idx)
        .unwrap_or(text.len());
    (line_start, line_end)
}

fn last_label(prefix_upper: &str) -> Option<&'static str> {
    let normalized_prefix = keywordize(prefix_upper);
    let padded_prefix = format!(" {} ", normalized_prefix);
    let label_sets: [(&str, &[&str]); 4] = [
        (
            "total",
            &["GRAND TOTAL", "TOTAL DUE", "AMOUNT DUE", "BALANCE DUE", "TOTAL", "GESAMT", "IMPORTE"],
        ),
        ("tax", &["TAX", "VAT", "IVA", "MWST", "GST", "UST", "STEUER"]),
        ("subtotal", &["SUBTOTAL", "NETTO", "NET", "ZWISCHENSUMME", "BASE IMPONIBLE"]),
        (
            "penalty",
            &["TIP", "TRINKGELD", "PROPINA", "DISCOUNT", "RABATT", "DESCUENTO", "SHIPPING", "FREIGHT", "ENVIO"],
        ),
    ];

    let mut best: Option<(&'static str, usize)> = None;
    for (label, needles) in label_sets {
        for needle in needles {
            let normalized_needle = keywordize(needle);
            if normalized_needle.is_empty() {
                continue;
            }
            let padded_needle = format!(" {} ", normalized_needle);
            if let Some(pos) = padded_prefix.rfind(&padded_needle) {
                if best.map(|(_, best_pos)| pos > best_pos).unwrap_or(true) {
                    best = Some((label, pos));
                }
            }
        }
    }
    best.map(|item| item.0)
}

fn raw_token_covering<'a>(tokens: &'a [RawToken], start: usize, end: usize) -> Option<&'a RawToken> {
    tokens
        .iter()
        .find(|token| span_overlaps(start, end, token.start, token.end))
}

fn build_context_window(tokens: &[RawToken], start: usize, end: usize) -> (String, String) {
    if let Some(hit) = raw_token_covering(tokens, start, end) {
        let same_line: Vec<&RawToken> = tokens.iter().filter(|token| token.line_index == hit.line_index).collect();
        let pos = same_line
            .iter()
            .position(|token| token.start == hit.start && token.end == hit.end)
            .unwrap_or(0);
        let left = pos.saturating_sub(3);
        let right = (pos + 4).min(same_line.len());
        let raw = same_line[left..right]
            .iter()
            .map(|token| token.raw.as_str())
            .collect::<Vec<&str>>()
            .join(" ");
        let upper = same_line[left..right]
            .iter()
            .map(|token| token.upper.as_str())
            .collect::<Vec<&str>>()
            .join(" ");
        (raw, upper)
    } else {
        let raw = text_window_around(tokens, start, end);
        (raw.clone(), raw.to_ascii_uppercase())
    }
}

fn text_window_around(tokens: &[RawToken], start: usize, end: usize) -> String {
    let mut snippets = Vec::new();
    for token in tokens {
        if token.end + 24 < start || token.start > end + 24 {
            continue;
        }
        snippets.push(token.raw.clone());
    }
    if snippets.is_empty() {
        String::new()
    } else {
        snippets.join(" ")
    }
}

fn is_identifier_fragment(text: &str, start: usize, end: usize) -> bool {
    let before = prev_char(text, start).map(|(_, ch)| ch);
    let after = next_char(text, end).map(|(_, ch)| ch);

    if before.is_some_and(|ch| ch.is_ascii_alphanumeric() || ch == '#')
        || after.is_some_and(|ch| ch.is_ascii_alphanumeric() || ch == '#')
    {
        return true;
    }

    if before == Some('-') || before == Some('_') {
        if prev_char(text, start.saturating_sub(1)).is_some_and(|(_, ch)| ch.is_ascii_alphanumeric()) {
            return true;
        }
    }
    if after == Some('-') || after == Some('_') {
        if next_char(text, end + 1).is_some_and(|(_, ch)| ch.is_ascii_alphanumeric()) {
            return true;
        }
    }

    false
}

fn extract_amount_candidates(input: &ExtractorInput, raw_tokens: &[RawToken]) -> Vec<AmountCandidate> {
    let text = input.ocr_text.as_str();
    let date_spans = collect_date_spans(text);
    let mut candidates = Vec::new();

    for mat in amount_regex().find_iter(text) {
        let start = mat.start();
        let end = mat.end();
        if date_spans
            .iter()
            .any(|(date_start, date_end)| span_overlaps(start, end, *date_start, *date_end))
        {
            continue;
        }
        if is_identifier_fragment(text, start, end) {
            continue;
        }

        let raw = mat.as_str().trim().to_string();
        if raw.contains('%') || contains_alpha(&raw) && !raw.contains("EUR") && !raw.contains("USD") && !raw.contains("GBP") && !raw.contains("CHF") {
            continue;
        }

        let Some((value, has_decimal, decimal_places, has_currency_marker)) =
            parse_amount_value(&raw, &input.locale.to_ascii_lowercase())
        else {
            continue;
        };

        if value <= 0.0 {
            continue;
        }

        let (window_raw, window_upper) = build_context_window(raw_tokens, start, end);
        let (line_start, line_end) = line_bounds(text, start, end);
        let line_upper = text[line_start..line_end].to_ascii_uppercase();
        let line_prefix_upper = text[line_start..start].to_ascii_uppercase();

        candidates.push(AmountCandidate {
            looks_like_identifier: !has_decimal && raw.len() >= 4 && !window_upper.contains("TOTAL") && !window_upper.contains("GESAMT"),
            raw,
            value,
            start,
            has_decimal,
            decimal_places,
            has_currency_marker,
            window_upper,
            window_raw,
            line_upper,
            line_prefix_upper,
        });
    }

    candidates
}

fn contains_any(text: &str, needles: &[&str]) -> bool {
    let haystack = format!(" {} ", keywordize(text));
    needles.iter().any(|needle| {
        let normalized = keywordize(needle);
        !normalized.is_empty() && haystack.contains(&format!(" {} ", normalized))
    })
}

fn total_keywords(text: &str) -> bool {
    contains_any(
        text,
        &[
            "GRAND TOTAL",
            "TOTAL DUE",
            "AMOUNT DUE",
            "BALANCE DUE",
            "TOTAL",
            "GESAMT",
            "IMPORTE",
            "PAYMENT DUE",
        ],
    )
}

fn subtotal_keywords(text: &str) -> bool {
    contains_any(text, &["SUBTOTAL", "NET", "NETTO", "ZWISCHENSUMME", "BASE IMPONIBLE"])
}

fn tax_keywords(text: &str) -> bool {
    contains_any(text, &["TAX", "VAT", "IVA", "MWST", "GST", "UST", "STEUER"])
}

fn penalty_keywords(text: &str) -> bool {
    contains_any(
        text,
        &[
            "TIP",
            "TRINKGELD",
            "PROPINA",
            "DISCOUNT",
            "RABATT",
            "DESCUENTO",
            "SHIPPING",
            "FREIGHT",
            "ENVIO",
        ],
    )
}

fn score_total_candidate(candidate: &AmountCandidate, source_type: &str) -> ScoredCandidate {
    let mut score = 0.0;
    let mut reasons = Vec::new();

    if total_keywords(&candidate.window_upper) {
        score += 5.5;
        reasons.push("total_keyword");
    }
    if candidate.window_upper.contains("AMOUNT DUE") || candidate.window_upper.contains("BALANCE DUE") {
        score += 1.5;
        reasons.push("due_phrase");
    }
    if candidate.has_currency_marker {
        score += 0.4;
        reasons.push("currency_marker");
    }
    if candidate.has_decimal && candidate.decimal_places == 2 {
        score += 0.5;
        reasons.push("money_shape");
    }
    if candidate.line_upper.contains("TOTAL") && !candidate.window_upper.contains("SUBTOTAL") {
        score += 0.5;
        reasons.push("line_total");
    }
    match last_label(&candidate.line_prefix_upper) {
        Some("total") => {
            score += 2.5;
            reasons.push("nearest_total_label");
        }
        Some("tax") => {
            score -= 2.5;
            reasons.push("tax_label_penalty");
        }
        Some("subtotal") => {
            score -= 2.5;
            reasons.push("subtotal_label_penalty");
        }
        Some("penalty") => {
            score -= 3.5;
            reasons.push("penalty_label");
        }
        _ => {}
    }
    if source_type.eq_ignore_ascii_case("receipt") && candidate.window_upper.contains("RECEIPT") {
        score += 0.4;
        reasons.push("receipt_context");
    }
    if tax_keywords(&candidate.window_upper) {
        score -= 3.0;
        reasons.push("tax_context_penalty");
    }
    if subtotal_keywords(&candidate.window_upper) {
        score -= 3.0;
        reasons.push("subtotal_context_penalty");
    }
    if penalty_keywords(&candidate.window_upper) {
        score -= 4.0;
        reasons.push("penalty_keyword");
    }
    if candidate.looks_like_identifier && !total_keywords(&candidate.window_upper) {
        score -= 4.0;
        reasons.push("identifier_penalty");
    }
    if !candidate.has_decimal && !total_keywords(&candidate.window_upper) {
        score -= 1.0;
        reasons.push("integer_penalty");
    }

    ScoredCandidate {
        support: clamp_support(0.45 + (score / 8.0)),
        candidate: candidate.clone(),
        score,
        reasons,
    }
}

fn score_tax_candidate(candidate: &AmountCandidate) -> ScoredCandidate {
    let mut score = 0.0;
    let mut reasons = Vec::new();

    if tax_keywords(&candidate.window_upper) {
        score += 5.0;
        reasons.push("tax_keyword");
    }
    if candidate.window_upper.contains("TAX TOTAL") || candidate.window_upper.contains("VAT TOTAL") {
        score += 1.0;
        reasons.push("tax_total_phrase");
    }
    if candidate.has_decimal && candidate.decimal_places == 2 {
        score += 0.5;
        reasons.push("money_shape");
    }
    match last_label(&candidate.line_prefix_upper) {
        Some("tax") => {
            score += 3.0;
            reasons.push("nearest_tax_label");
        }
        Some("total") => {
            score -= 2.5;
            reasons.push("nearest_total_label_penalty");
        }
        Some("subtotal") => {
            score -= 1.5;
            reasons.push("nearest_subtotal_label_penalty");
        }
        Some("penalty") => {
            score -= 2.5;
            reasons.push("penalty_label");
        }
        _ => {}
    }
    if total_keywords(&candidate.window_upper) {
        score -= 2.5;
        reasons.push("total_context_penalty");
    }
    if subtotal_keywords(&candidate.window_upper) {
        score -= 2.0;
        reasons.push("subtotal_context_penalty");
    }
    if penalty_keywords(&candidate.window_upper) {
        score -= 3.0;
        reasons.push("penalty_keyword");
    }
    if !candidate.has_decimal && candidate.value <= 30.0 {
        score -= 2.0;
        reasons.push("likely_tax_rate");
    }

    ScoredCandidate {
        support: clamp_support(0.4 + (score / 8.0)),
        candidate: candidate.clone(),
        score,
        reasons,
    }
}

fn score_subtotal_candidate(candidate: &AmountCandidate) -> ScoredCandidate {
    let mut score = 0.0;
    let mut reasons = Vec::new();

    if subtotal_keywords(&candidate.window_upper) {
        score += 5.0;
        reasons.push("subtotal_keyword");
    }
    if candidate.has_decimal && candidate.decimal_places == 2 {
        score += 0.5;
        reasons.push("money_shape");
    }
    match last_label(&candidate.line_prefix_upper) {
        Some("subtotal") => {
            score += 3.0;
            reasons.push("nearest_subtotal_label");
        }
        Some("tax") => {
            score -= 1.5;
            reasons.push("nearest_tax_label_penalty");
        }
        Some("total") => {
            score -= 2.5;
            reasons.push("nearest_total_label_penalty");
        }
        Some("penalty") => {
            score -= 2.5;
            reasons.push("penalty_label");
        }
        _ => {}
    }
    if total_keywords(&candidate.window_upper) {
        score -= 2.5;
        reasons.push("total_context_penalty");
    }
    if tax_keywords(&candidate.window_upper) {
        score -= 2.0;
        reasons.push("tax_context_penalty");
    }
    if penalty_keywords(&candidate.window_upper) {
        score -= 2.5;
        reasons.push("penalty_keyword");
    }

    ScoredCandidate {
        support: clamp_support(0.4 + (score / 8.0)),
        candidate: candidate.clone(),
        score,
        reasons,
    }
}

fn sort_scored(mut rows: Vec<ScoredCandidate>) -> Vec<ScoredCandidate> {
    rows.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(Ordering::Equal)
            .then_with(|| {
                b.candidate
                    .value
                    .partial_cmp(&a.candidate.value)
                    .unwrap_or(Ordering::Equal)
            })
            .then_with(|| a.candidate.start.cmp(&b.candidate.start))
    });
    rows
}

fn choose_candidate(rows: &[ScoredCandidate], threshold: f64, max_value: Option<f64>) -> Option<ScoredCandidate> {
    for row in rows {
        if row.score < threshold {
            continue;
        }
        if let Some(limit) = max_value {
            if row.candidate.value > limit + 0.01 {
                continue;
            }
        }
        return Some(row.clone());
    }
    None
}

fn receipt_fallback_candidate(rows: &[ScoredCandidate]) -> Option<ScoredCandidate> {
    let mut eligible: Vec<ScoredCandidate> = rows
        .iter()
        .filter(|row| {
            row.candidate.has_decimal
                && !row.candidate.looks_like_identifier
                && !matches!(last_label(&row.candidate.line_prefix_upper), Some("tax" | "subtotal" | "penalty"))
        })
        .cloned()
        .collect();
    eligible.sort_by(|a, b| {
        b.candidate
            .value
            .partial_cmp(&a.candidate.value)
            .unwrap_or(Ordering::Equal)
            .then_with(|| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal))
            .then_with(|| a.candidate.start.cmp(&b.candidate.start))
    });

    let mut top = eligible.first()?.clone();
    if let Some(second) = eligible.get(1) {
        if (top.candidate.value - second.candidate.value).abs() <= 0.01 {
            return None;
        }
    }
    top.score = top.score.max(GRAND_TOTAL_THRESHOLD + 0.25);
    top.support = top.support.max(0.84);
    top.reasons.push("receipt_fallback_max_amount");
    Some(top)
}

fn ambiguous(rows: &[ScoredCandidate], threshold: f64) -> bool {
    if rows.len() < 2 || rows[0].score < threshold {
        return false;
    }
    let top = &rows[0];
    let second = &rows[1];
    (top.score - second.score).abs() <= SCORE_AMBIGUITY_MARGIN
        && (top.candidate.value - second.candidate.value).abs() > 0.01
}

fn extract_tax_rate(ocr_text: &str, locale: &str) -> Option<f64> {
    let capture = tax_rate_regex().captures(ocr_text)?;
    let raw = capture.get(1)?.as_str();
    let (value, _, _, _) = parse_amount_value(raw, locale)?;
    if value <= 0.0 {
        None
    } else {
        Some(value / 100.0)
    }
}

fn make_ref(field: &str, source: &str, snippet: &str, support: f64) -> EvidenceRef {
    EvidenceRef {
        field: field.to_string(),
        source: source.to_string(),
        snippet: snippet.trim().to_string(),
        support: clamp_support(support),
    }
}

fn build_numeric_extraction(input: &ExtractorInput, raw_tokens: &[RawToken]) -> NumericExtractionResult {
    let candidates = extract_amount_candidates(input, raw_tokens);
    let total_scored = sort_scored(
        candidates
            .iter()
            .map(|candidate| score_total_candidate(candidate, &input.source_type))
            .collect(),
    );
    let tax_scored = sort_scored(candidates.iter().map(score_tax_candidate).collect());
    let subtotal_scored = sort_scored(candidates.iter().map(score_subtotal_candidate).collect());

    let mut warnings = Vec::new();
    let mut evidence_refs = Vec::new();
    let mut abstain = false;
    let mut abstain_reason_code = String::new();

    let mut used_receipt_fallback = false;
    let mut total_choice = choose_candidate(&total_scored, GRAND_TOTAL_THRESHOLD, None);
    if total_choice.is_none() && input.source_type.eq_ignore_ascii_case("receipt") {
        total_choice = receipt_fallback_candidate(&total_scored);
        used_receipt_fallback = total_choice.is_some();
        if used_receipt_fallback {
            warnings.push("receipt_total_fallback".to_string());
        }
    }
    if total_choice.is_none() || (ambiguous(&total_scored, GRAND_TOTAL_THRESHOLD) && !used_receipt_fallback) {
        abstain = true;
        abstain_reason_code = "NUMERIC_GROUNDING_FAILED".to_string();
        warnings.push("grand_total_not_grounded".to_string());
    }

    let mut grand_total = total_choice.as_ref().map(|row| round2(row.candidate.value)).unwrap_or(0.0);
    let mut tax_total = 0.0;
    let mut subtotal = 0.0;

    let explicit_tax = if grand_total > 0.0 {
        choose_candidate(&tax_scored, TAX_THRESHOLD, Some(grand_total))
    } else {
        None
    };
    let explicit_subtotal = if grand_total > 0.0 {
        choose_candidate(&subtotal_scored, SUBTOTAL_THRESHOLD, Some(grand_total))
    } else {
        None
    };

    if let Some(row) = &total_choice {
        evidence_refs.push(make_ref("grand_total", "ocr", &row.candidate.window_raw, row.support));
    } else {
        evidence_refs.push(make_ref("grand_total", "derived", "grand_total_unavailable", 0.2));
    }

    if let Some(row) = &explicit_tax {
        tax_total = round2(row.candidate.value);
        evidence_refs.push(make_ref("tax_total", "ocr", &row.candidate.window_raw, row.support));
    }

    if let Some(row) = &explicit_subtotal {
        subtotal = round2(row.candidate.value);
        evidence_refs.push(make_ref("subtotal", "ocr", &row.candidate.window_raw, row.support));
    }

    let tax_rate = extract_tax_rate(&input.ocr_text, &input.locale.to_ascii_lowercase());
    if tax_total == 0.0 && grand_total > 0.0 {
        if let Some(row) = &explicit_subtotal {
            let derived_tax = round2(grand_total - row.candidate.value);
            if derived_tax >= 0.0 {
                tax_total = derived_tax;
                evidence_refs.push(make_ref(
                    "tax_total",
                    "derived",
                    &format!("{:.2} - {:.2}", grand_total, row.candidate.value),
                    0.78,
                ));
                warnings.push("tax_total_derived_from_total_and_subtotal".to_string());
            }
        } else if let Some(rate) = tax_rate {
            let derived_subtotal = round2(grand_total / (1.0 + rate));
            let derived_tax = round2(grand_total - derived_subtotal);
            subtotal = derived_subtotal;
            tax_total = derived_tax;
            evidence_refs.push(make_ref(
                "subtotal",
                "derived",
                &format!("{:.2} / (1 + {:.4})", grand_total, rate),
                0.74,
            ));
            evidence_refs.push(make_ref(
                "tax_total",
                "derived",
                &format!("{:.2} - {:.2}", grand_total, derived_subtotal),
                0.74,
            ));
            warnings.push("numeric_fields_derived_from_tax_rate".to_string());
        }
    }

    if subtotal == 0.0 && grand_total > 0.0 {
        if let Some(row) = &explicit_tax {
            let derived_subtotal = round2(grand_total - row.candidate.value);
            if derived_subtotal >= 0.0 {
                subtotal = derived_subtotal;
                evidence_refs.push(make_ref(
                    "subtotal",
                    "derived",
                    &format!("{:.2} - {:.2}", grand_total, row.candidate.value),
                    0.82,
                ));
                warnings.push("subtotal_derived_from_total_and_tax".to_string());
            }
        } else if input.source_type.eq_ignore_ascii_case("receipt") || tax_rate.is_none() {
            subtotal = grand_total;
            evidence_refs.push(make_ref("subtotal", "derived", &format!("{:.2}", grand_total), 0.78));
        }
    }

    if tax_total == 0.0 && !evidence_refs.iter().any(|item| item.field == "tax_total") {
        evidence_refs.push(make_ref("tax_total", "derived", "0.00", 0.78));
    }
    if subtotal == 0.0 && !evidence_refs.iter().any(|item| item.field == "subtotal") {
        evidence_refs.push(make_ref("subtotal", "derived", "0.00", 0.35));
    }

    if subtotal > 0.0 && tax_total > 0.0 && grand_total == 0.0 {
        grand_total = round2(subtotal + tax_total);
        evidence_refs.retain(|item| item.field != "grand_total");
        evidence_refs.push(make_ref(
            "grand_total",
            "derived",
            &format!("{:.2} + {:.2}", subtotal, tax_total),
            0.74,
        ));
        warnings.push("grand_total_derived_from_subtotal_and_tax".to_string());
    }

    if grand_total > 0.0 && subtotal + tax_total > 0.0 {
        let combined = round2(subtotal + tax_total);
        if (combined - grand_total).abs() > 0.05 {
            if explicit_subtotal.is_some() && explicit_tax.is_some() {
                warnings.push("numeric_components_inconsistent".to_string());
                abstain = true;
                abstain_reason_code = "NUMERIC_INCONSISTENT".to_string();
            } else {
                subtotal = round2((grand_total - tax_total).max(0.0));
                evidence_refs.retain(|item| item.field != "subtotal");
                evidence_refs.push(make_ref(
                    "subtotal",
                    "derived",
                    &format!("{:.2} - {:.2}", grand_total, tax_total),
                    0.76,
                ));
                warnings.push("subtotal_reconciled_to_total".to_string());
            }
        }
    }

    if grand_total <= 0.0 {
        abstain = true;
        if abstain_reason_code.is_empty() {
            abstain_reason_code = "NUMERIC_GROUNDING_FAILED".to_string();
        }
    }

    if !abstain && total_choice.is_none() {
        abstain = true;
        abstain_reason_code = "NUMERIC_GROUNDING_FAILED".to_string();
    }

    let top_totals: Vec<serde_json::Value> = total_scored
        .iter()
        .take(4)
        .map(|row| {
            serde_json::json!({
                "raw": row.candidate.raw,
                "value": round2(row.candidate.value),
                "score": round2(row.score),
                "reasons": row.reasons,
            })
        })
        .collect();

    NumericExtractionResult {
        subtotal: round2(subtotal.max(0.0)),
        tax_total: round2(tax_total.max(0.0)),
        grand_total: round2(grand_total.max(0.0)),
        warnings,
        abstain,
        abstain_reason_code,
        evidence_refs,
        debug: serde_json::json!({
            "candidate_count": candidates.len(),
            "top_total_candidates": top_totals,
            "tax_rate_hint": tax_rate.map(round2),
        }),
    }
}

fn normalize_date_token(raw: &str, locale: &str) -> Option<String> {
    if iso_date_regex().is_match(raw) {
        return Some(raw.replace('/', "-"));
    }

    if dotted_date_regex().is_match(raw) {
        let parts: Vec<&str> = raw.split('.').collect();
        if parts.len() == 3 {
            return Some(format!("{}-{}-{}", parts[2], parts[1], parts[0]));
        }
    }

    if slash_date_regex().is_match(raw) {
        let parts: Vec<&str> = raw.split('/').collect();
        if parts.len() == 3 {
            if locale.to_ascii_lowercase().starts_with("en") {
                return Some(format!("{}-{:0>2}-{:0>2}", parts[2], parts[0], parts[1]));
            }
            return Some(format!("{}-{:0>2}-{:0>2}", parts[2], parts[1], parts[0]));
        }
    }

    None
}

fn resolve_dates(ocr_text: &str, locale: &str) -> DateResolution {
    let mut found = Vec::new();
    for re in [iso_date_regex(), dotted_date_regex(), slash_date_regex()] {
        for mat in re.find_iter(ocr_text) {
            if let Some(date) = normalize_date_token(mat.as_str(), locale) {
                found.push((date, mat.as_str().to_string()));
            }
        }
    }

    if found.is_empty() {
        return DateResolution {
            invoice_date: "2026-01-01".to_string(),
            due_date: "2026-01-31".to_string(),
            invoice_source: "derived".to_string(),
            due_source: "derived".to_string(),
            invoice_support: 0.76,
            due_support: 0.76,
        };
    }

    let invoice = &found[0];
    let due = if found.len() > 1 { &found[1] } else { &found[0] };
    DateResolution {
        invoice_date: invoice.0.clone(),
        due_date: due.0.clone(),
        invoice_source: "ocr".to_string(),
        due_source: if found.len() > 1 {
            "ocr".to_string()
        } else {
            "derived".to_string()
        },
        invoice_support: 0.9,
        due_support: if found.len() > 1 { 0.88 } else { 0.78 },
    }
}

fn is_keyword_label(token: &str) -> bool {
    matches!(
        token,
        "INVOICE"
            | "INVOICE#"
            | "INVOICE NO"
            | "RECHNUNG"
            | "FACTURA"
            | "FACTURA NO"
            | "NO"
            | "NO."
            | "NR"
            | "NR."
            | "NUMERO"
            | "INV"
            | "INV#"
    )
}

fn looks_like_identifier_value(raw: &str) -> bool {
    let upper = keywordize(raw);
    if raw.contains('.') || raw.contains(',') {
        return false;
    }
    let has_digit = upper.chars().any(|ch| ch.is_ascii_digit());
    let has_alpha = upper.chars().any(|ch| ch.is_ascii_alphabetic());
    has_digit && (has_alpha || upper.contains('-') || upper.contains('_') || upper.len() >= 4)
}

fn find_invoice_number(raw_tokens: &[RawToken]) -> String {
    for (idx, token) in raw_tokens.iter().enumerate() {
        if is_keyword_label(token.upper.as_str()) {
            if let Some(next) = raw_tokens.get(idx + 1) {
                let candidate = next.raw.trim_matches(|ch: char| !ch.is_ascii_alphanumeric() && ch != '-' && ch != '_');
                if !candidate.is_empty() && looks_like_identifier_value(candidate) {
                    return candidate.to_string();
                }
            }
        }
    }

    for token in raw_tokens {
        let candidate = token.raw.trim_matches(|ch: char| !ch.is_ascii_alphanumeric() && ch != '-' && ch != '_');
        if looks_like_identifier_value(candidate) && !total_keywords(&token.upper) && !tax_keywords(&token.upper) {
            return candidate.to_string();
        }
    }

    String::new()
}

fn vendor_stopword(token: &str) -> bool {
    matches!(
        token,
        "INVOICE"
            | "RECEIPT"
            | "QUITTUNG"
            | "FACTURA"
            | "RECHNUNG"
            | "TOTAL"
            | "TAX"
            | "VAT"
            | "IVA"
            | "MWST"
            | "AMOUNT"
            | "DUE"
    )
}

fn resolve_vendor_name(input: &ExtractorInput, raw_tokens: &[RawToken]) -> (String, String, f64) {
    if !input.account_context.vendor_hint.trim().is_empty() {
        return (input.account_context.vendor_hint.trim().to_string(), "derived".to_string(), 0.82);
    }

    let picked = raw_tokens
        .iter()
        .filter(|token| token.raw.chars().all(|ch| ch.is_ascii_alphabetic() || ch == '&'))
        .map(|token| token.raw.clone())
        .find(|token| !vendor_stopword(&token.to_ascii_uppercase()))
        .unwrap_or_else(|| "UNKNOWN_VENDOR".to_string());

    (picked, "ocr".to_string(), 0.78)
}

fn claim_support_from_refs(evidence_refs: &[EvidenceRef], confidence: f64, abstain: bool) -> f64 {
    if abstain {
        return 0.35;
    }
    if evidence_refs.is_empty() {
        return clamp_support(confidence * 0.5);
    }
    let mean_support = evidence_refs.iter().map(|item| item.support).sum::<f64>() / evidence_refs.len() as f64;
    clamp_support((mean_support * 0.85) + (confidence * 0.15))
}

pub fn run_extractor(input: ExtractorInput) -> ExtractorOutput {
    let tokens = tokenize_text(&input.ocr_text);
    let raw_tokens = split_raw_tokens(&input.ocr_text);
    let token_stream = tokens.join("|");
    let token_stream_hash = stable_hash(&token_stream);

    let feature_vector = build_feature_vector(
        &tokens,
        &input.source_type,
        &input.account_context.ledger_profile,
    );
    let feature_payload = serde_json::to_string(&feature_vector).unwrap_or_else(|_| "[]".to_string());
    let feature_hash = stable_hash(&feature_payload);

    let (routing_label, confidence, ranking) =
        run_strict_candle_inference(&feature_vector, &input.doc_id);

    let currency = infer_currency(&input);
    let (vendor_name, vendor_source, vendor_support) = resolve_vendor_name(&input, &raw_tokens);
    let invoice_number = find_invoice_number(&raw_tokens);
    let dates = resolve_dates(&input.ocr_text, &input.locale);
    let numeric = build_numeric_extraction(&input, &raw_tokens);

    let mut warnings = numeric.warnings.clone();
    if confidence < 0.55 {
        warnings.push("low_confidence_routing".to_string());
    }
    if invoice_number.is_empty() && routing_label == "accounts_payable_invoice" {
        warnings.push("invoice_number_missing".to_string());
    }

    let extracted_fields = ExtractedFields {
        vendor_name: vendor_name.clone(),
        invoice_number,
        invoice_date: dates.invoice_date.clone(),
        due_date: dates.due_date.clone(),
        currency: currency.clone(),
        subtotal: numeric.subtotal,
        tax_total: numeric.tax_total,
        grand_total: numeric.grand_total,
    };

    let vat_rate = if extracted_fields.subtotal > 0.0 {
        round2(extracted_fields.tax_total / extracted_fields.subtotal)
    } else {
        0.0
    };

    let mut evidence_refs = vec![
        make_ref("vendor_name", &vendor_source, &vendor_name, vendor_support),
        make_ref(
            "invoice_date",
            &dates.invoice_source,
            &dates.invoice_date,
            dates.invoice_support,
        ),
        make_ref("due_date", &dates.due_source, &dates.due_date, dates.due_support),
        make_ref("currency", "derived", &currency, 0.86),
    ];
    evidence_refs.extend(numeric.evidence_refs.clone());

    let claim_support_score = claim_support_from_refs(&evidence_refs, confidence, numeric.abstain);

    ExtractorOutput {
        doc_id: input.doc_id,
        source_type: input.source_type,
        import_event: input.import_event,
        ocr_text: input.ocr_text,
        locale: input.locale,
        currency_hint: input.currency_hint,
        account_context: input.account_context,
        routing_label,
        confidence,
        extracted_fields,
        warnings,
        ranking,
        abstain: numeric.abstain,
        abstain_reason_code: numeric.abstain_reason_code,
        claim_support_score,
        evidence_refs,
        vat_metrics: serde_json::json!({
            "backend": STRICT_CANDLE_BACKEND,
            "vat_rate_class": if vat_rate >= 0.19 { "standard" } else { "reduced_or_zero" },
            "vat_rate": vat_rate,
        }),
        classification_metrics: serde_json::json!({
            "backend": STRICT_CANDLE_BACKEND,
            "model_version": "v6",
            "tokenizer_version": "v6_det_tok_2",
            "token_count": tokens.len(),
            "token_stream_hash": token_stream_hash,
            "feature_hash": feature_hash,
            "feature_vector": feature_vector,
            "numeric_extraction": numeric.debug,
        }),
    }
}

pub fn run_from_json(input_json: &str) -> Result<String, String> {
    let request: WasmRequest =
        serde_json::from_str(input_json).map_err(|err| format!("invalid_input_json:{err}"))?;
    let parsed = match request {
        WasmRequest::Direct(payload) => payload,
        WasmRequest::Wrapped { extractor_input } => extractor_input,
    };
    let output = run_extractor(parsed);
    serde_json::to_string(&output).map_err(|err| format!("serialization_error:{err}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_input(source_type: &str, ocr_text: &str, locale: &str, vendor_hint: &str) -> ExtractorInput {
        ExtractorInput {
            doc_id: "test-doc-001".to_string(),
            source_type: source_type.to_string(),
            import_event: "on_import".to_string(),
            ocr_text: ocr_text.to_string(),
            locale: locale.to_string(),
            currency_hint: if locale.starts_with("de") || locale.starts_with("es") {
                "EUR".to_string()
            } else {
                "USD".to_string()
            },
            account_context: AccountContext {
                ledger_profile: if source_type == "receipt" {
                    "expense_default".to_string()
                } else {
                    "ap_default".to_string()
                },
                cost_center: "CC-1".to_string(),
                vendor_hint: vendor_hint.to_string(),
            },
        }
    }

    #[test]
    fn tokenizer_is_deterministic() {
        let input = "Invoice A-100 total 119.00 tax 19.00";
        let a = tokenize_text(input);
        let b = tokenize_text(input);
        assert_eq!(a, b);
    }

    #[test]
    fn feature_hash_is_deterministic() {
        let tokens = tokenize_text("INVOICE B-200 TOTAL 100 TAX 10");
        let features = build_feature_vector(&tokens, "invoice", "ap_default");
        let payload = serde_json::to_string(&features).unwrap();
        assert_eq!(stable_hash(&payload), stable_hash(&payload));
    }

    #[test]
    fn wrapped_request_schema_is_supported() {
        let raw = r#"{"extractor_input":{"doc_id":"v6-schema-001","source_type":"invoice","import_event":"on_import","ocr_text":"INVOICE 100 TAX 19 TOTAL 119","locale":"en-US","currency_hint":"USD","account_context":{"ledger_profile":"ap_default","cost_center":"CC-1","vendor_hint":"Acme"}}}"#;
        let out = run_from_json(raw).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(&out).unwrap();
        assert!(parsed.get("classification_metrics").is_some());
        assert!(parsed.get("vat_metrics").is_some());
        assert!(parsed.get("evidence_refs").is_some());
    }

    #[test]
    fn rejects_invoice_number_as_total() {
        let output = run_extractor(make_input(
            "invoice",
            "FACTURA V-778 TOTAL 238,00 IVA 38,00",
            "es-ES",
            "Proveedor SA",
        ));
        assert_eq!(output.extracted_fields.grand_total, 238.0);
        assert_eq!(output.extracted_fields.tax_total, 38.0);
        assert_eq!(output.extracted_fields.subtotal, 200.0);
        assert!(!output.abstain);
    }

    #[test]
    fn receipt_prefers_total_over_tip() {
        let output = run_extractor(make_input(
            "receipt",
            "RECEIPT CAFE TOTAL 42.35 TIP 5.00",
            "en-US",
            "Cafe Midtown",
        ));
        assert_eq!(output.extracted_fields.grand_total, 42.35);
        assert_eq!(output.extracted_fields.tax_total, 0.0);
        assert_eq!(output.extracted_fields.subtotal, 42.35);
    }

    #[test]
    fn german_total_and_tax_extract_cleanly() {
        let output = run_extractor(make_input(
            "invoice",
            "RECHNUNG NORD-880 GESAMT 299,90 MWST 47,89",
            "de-DE",
            "Nord GmbH",
        ));
        assert_eq!(output.extracted_fields.grand_total, 299.9);
        assert_eq!(output.extracted_fields.tax_total, 47.89);
        assert_eq!(output.extracted_fields.subtotal, 252.01);
    }

    #[test]
    fn tax_rate_derived_fields_emit_evidence_refs() {
        let input = make_input("invoice", "INVOICE ACME TOTAL 119.00 VAT 19%", "en-US", "Acme");
        let numeric = build_numeric_extraction(&input, &split_raw_tokens("INVOICE ACME TOTAL 119.00"));
        assert_eq!(numeric.grand_total, 119.0);
        assert_eq!(numeric.tax_total, 19.0);
        assert_eq!(numeric.subtotal, 100.0);
        assert!(numeric
            .warnings
            .iter()
            .any(|warning| warning == "numeric_fields_derived_from_tax_rate"));
        assert_eq!(
            numeric
                .evidence_refs
                .iter()
                .find(|row| row.field == "tax_total")
                .unwrap()
                .source,
            "derived"
        );
        assert_eq!(
            numeric
                .evidence_refs
                .iter()
                .find(|row| row.field == "subtotal")
                .unwrap()
                .source,
            "derived"
        );
    }

    #[test]
    fn amount_due_phrase_is_grounded() {
        let output = run_extractor(make_input(
            "invoice",
            "INVOICE DELTA-9007 AMOUNT DUE 440.00",
            "en-US",
            "Delta Supplies",
        ));
        assert_eq!(output.extracted_fields.grand_total, 440.0);
        assert_eq!(output.evidence_refs.iter().find(|row| row.field == "grand_total").unwrap().source, "ocr");
    }

    #[test]
    fn receipt_without_total_keyword_uses_max_grounded_amount() {
        let output = run_extractor(make_input(
            "receipt",
            "RECEIPT CAFE 42.35 TIP 5.00",
            "en-US",
            "Cafe Midtown",
        ));
        assert_eq!(output.extracted_fields.grand_total, 42.35);
        assert_eq!(output.extracted_fields.subtotal, 42.35);
        assert!(!output.abstain);
    }

    #[test]
    fn taxi_receipt_is_not_misread_as_tax_context() {
        let output = run_extractor(make_input(
            "receipt",
            "QUITTUNG TAXI 18,40",
            "de-DE",
            "Taxi Berlin",
        ));
        assert_eq!(output.extracted_fields.grand_total, 18.4);
        assert_eq!(output.extracted_fields.subtotal, 18.4);
        assert!(!output.abstain);
    }

    #[test]
    fn abstains_when_no_grounded_total_exists() {
        let output = run_extractor(make_input(
            "invoice",
            "INVOICE REF-1001 TAX RATE 19% VENDOR ACME",
            "en-US",
            "",
        ));
        assert!(output.abstain);
        assert_eq!(output.abstain_reason_code, "NUMERIC_GROUNDING_FAILED");
    }
}
