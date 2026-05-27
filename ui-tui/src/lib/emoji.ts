const VS15 = 0xfe0e
const VS16 = 0xfe0f
const KEYCAP = 0x20e3

const TEXT_DEFAULT_EMOJI = new Set<number>([
  0x00a9, 0x00ae, 0x203c, 0x2049, 0x2122, 0x2139, 0x2194, 0x2195, 0x2196, 0x2197, 0x2198, 0x2199, 0x21a9, 0x21aa,
  0x2328, 0x23cf, 0x23ed, 0x23ee, 0x23ef, 0x23f1, 0x23f2, 0x23f8, 0x23f9, 0x23fa, 0x24c2, 0x25aa, 0x25ab, 0x25b6,
  0x25c0, 0x25fb, 0x25fc, 0x2600, 0x2601, 0x2602, 0x2603, 0x2604, 0x260e, 0x2611, 0x2618, 0x261d, 0x2620, 0x2622,
  0x2623, 0x2626, 0x262a, 0x262e, 0x262f, 0x2638, 0x2639, 0x263a, 0x2640, 0x2642, 0x265f, 0x2660, 0x2663, 0x2665,
  0x2666, 0x2668, 0x267b, 0x267e, 0x2692, 0x2694, 0x2695, 0x2696, 0x2697, 0x2699, 0x269b, 0x269c, 0x26a0, 0x26a7,
  0x26b0, 0x26b1, 0x26c8, 0x26cf, 0x26d1, 0x26d3, 0x26d4, 0x26e9, 0x26f0, 0x26f1, 0x26f4, 0x26f7, 0x26f8, 0x26f9,
  0x2702, 0x2708, 0x2709, 0x270c, 0x270d, 0x270f, 0x2712, 0x2714, 0x2716, 0x271d, 0x2721, 0x2733, 0x2734, 0x2744,
  0x2747, 0x2763, 0x2764, 0x27a1, 0x2934, 0x2935, 0x2b05, 0x2b06, 0x2b07, 0x3030, 0x303d, 0x3297, 0x3299
])

const MAYBE_TEXT_EMOJI_RE =
  /[©®‼⁉™ℹ↔-↙↩↪⌨⏏⏭-⏯⏱⏲⏸-⏺Ⓜ▪▫▶◀◻◼☀-☄☎☑☘☝☠☢☣☦☪☮☯☸-☺♀♂♟♠♣♥♦♨♻♾⚒⚔-⚗⚙⚛⚜⚠⚧⚰⚱⛈⛏⛑⛓⛔⛩⛰⛱⛴⛷-⛹✂✈✉✌✍✏✒✔✖✝✡✳✴❄❇❣❤➡⤴⤵⬅-⬇〰〽㊗㊙]/

export function ensureEmojiPresentation(text: string): string {
  if (!text || !MAYBE_TEXT_EMOJI_RE.test(text)) {
    return text
  }

  // Lazy output: only start building when we actually need to insert VS16.
  // Short-circuits the whole walk for strings where every text-default emoji
  // is already followed by VS16/VS15, avoiding per-codepoint string growth.
  let out: null | string = null
  let last = 0
  let i = 0

  while (i < text.length) {
    const cp = text.codePointAt(i)!
    const size = cp > 0xffff ? 2 : 1

    if (TEXT_DEFAULT_EMOJI.has(cp)) {
      const next = text.codePointAt(i + size)

      // Skip only when the sequence already carries an explicit presentation
      // selector.  VS16 means the user (or a prior pass) already requested
      // emoji presentation; VS15 is an explicit text-presentation request so
      // leave it alone and don't pile VS16 on top of it.  Inject before ZWJ
      // and KEYCAP so ZWJ-joined sequences (e.g. ❤️‍🔥) and digit keycaps
      // both render as emoji rather than text.
      if (next !== VS16 && next !== VS15) {
        out ??= ''
        out += text.slice(last, i + size) + '️'
        last = i + size
      }
    }

    i += size
  }

  return out === null ? text : out + text.slice(last)
}
