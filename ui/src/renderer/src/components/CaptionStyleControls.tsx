import { useEffect, useState } from 'react'
import type { CaptionStyle } from '../lib/types'
import { t } from '../lib/i18n'

export const DEFAULT_CAPTION_STYLE: Required<CaptionStyle> = {
  font: 'Arial',
  font_size: 84,
  color: '#FFFFFF',
  position: 'bottom',
  outline_width: 7,
  outline_color: '#000000',
  background_style: 'none',
  background_color: '#000000',
  background_opacity: 0.7,
  words_per_caption: 3,
  uppercase: true,
  highlight: false,
  highlight_color: '#FFE600',
  second_speaker: false,
  second_speaker_color: '#5CE1FF'
}

/** Shared Windows fonts plus native macOS choices accepted by video/captions.py. */
const STOCK_CAPTION_FONTS = [
  'Arial',
  'Arial Black',
  'Impact',
  'Verdana',
  'Tahoma',
  'Trebuchet MS',
  'Segoe UI',
  'Georgia',
  'Comic Sans MS',
  'Courier New'
]
export const CAPTION_FONTS = [
  ...STOCK_CAPTION_FONTS,
  ...(window.studio?.platform === 'darwin'
    ? ['Avenir Next', 'Helvetica Neue', 'Menlo', 'Kohinoor Devanagari', 'Kohinoor Bangla']
    : [])
]

/** Live example of how the burned-in captions will look (9:16 mock). */
function CaptionExample({ style }: { style: Required<CaptionStyle> }): JSX.Element {
  // Show one caption group of exactly words_per_caption words — the same
  // grouping the burn-in uses, so changing the setting changes the example.
  const sample = ['your', 'captions', 'look', 'like', 'this', 'onscreen']
  const words = sample.slice(0, Math.max(1, Math.min(6, style.words_per_caption)))
  const text = style.uppercase ? words.join(' ').toUpperCase() : words.join(' ')
  // Cycle the highlight through the words so the example shows the effect
  // moving, which is the whole point of it.
  const [hot, setHot] = useState(0)
  useEffect(() => {
    if (!style.highlight) return
    const id = setInterval(() => setHot((h) => (h + 1) % words.length), 550)
    return () => clearInterval(id)
  }, [style.highlight, words.length])
  const align =
    style.position === 'top' ? 'items-start' : style.position === 'middle' ? 'items-center' : 'items-end'
  return (
    <div
      className={`relative rounded-lg bg-gradient-to-br from-slate-700 via-slate-800 to-slate-900 aspect-[9/16] max-h-44 mx-auto w-auto flex ${align} justify-center overflow-hidden`}
      aria-label={t('Caption style example')}
    >
      <p
        className="text-center px-2 py-4 leading-tight"
        style={{
          fontFamily: `'${style.font}', sans-serif`,
          color: style.color,
          // 84px at 1920 tall ≈ scale into this ~176px-tall mock
          fontSize: `${(style.font_size / 1920) * 176 * 2.2}px`,
          fontWeight: 700,
          WebkitTextStroke: `${Math.max(0, style.outline_width * 0.3)}px ${style.outline_color}`,
          textShadow: style.outline_width > 0 ? '1px 1px 2px rgba(0,0,0,0.9)' : 'none',
          borderRadius: style.background_style === 'box' ? '6px' : undefined,
          background: style.background_style === 'box'
            ? `${style.background_color}${Math.round(style.background_opacity * 255).toString(16).padStart(2, '0')}`
            : undefined
        }}
      >
        {style.highlight
          ? words.map((w, i) => (
              <span key={i} style={{ color: i === hot ? style.highlight_color : style.color }}>
                {(style.uppercase ? w.toUpperCase() : w) + (i < words.length - 1 ? ' ' : '')}
              </span>
            ))
          : text}
        {/* The other speaker's caption, as it follows the main speaker's:
            the two colours side by side are what is being chosen. */}
        {style.second_speaker && (
          <span className="block" style={{ color: style.second_speaker_color }}>
            {style.uppercase ? 'SECOND SPEAKER' : 'second speaker'}
          </span>
        )}
      </p>
    </div>
  )
}

/** The caption style controls (colour, size, position, words, casing),
 *  shared between the Generate bar (style for all new clips) and the
 *  per-clip caption editor. */
export default function CaptionStyleControls({
  idPrefix,
  style,
  onChange,
  hideWordsPerCaption = false,
  hideSecondSpeaker = false
}: {
  idPrefix: string
  style: Required<CaptionStyle>
  onChange: <K extends keyof CaptionStyle>(key: K, value: CaptionStyle[K]) => void
  /** Translated subtitles inherit their grouping from the lines they
   *  replace, so regrouping does nothing there — hide it rather than offer
   *  a control that silently has no effect. */
  hideWordsPerCaption?: boolean
  /** Translated subtitles are burned in one colour, whoever is talking. */
  hideSecondSpeaker?: boolean
}): JSX.Element {
  const applyPreset = (preset: string): void => {
    if (preset === 'clean') {
      onChange('font', 'Arial')
      onChange('font_size', 60)
      onChange('color', '#FFFFFF')
      onChange('position', 'bottom')
      onChange('outline_width', 2)
      onChange('outline_color', '#000000')
      onChange('background_style', 'none')
      onChange('background_color', '#000000')
      onChange('background_opacity', 0.7)
      if (!hideWordsPerCaption) onChange('words_per_caption', 4)
      onChange('uppercase', false)
      onChange('highlight', false)
      onChange('highlight_color', '#FFE600')
      if (!hideSecondSpeaker) {
        onChange('second_speaker', false)
        onChange('second_speaker_color', '#5CE1FF')
      }
    } else if (preset === 'karaoke') {
      onChange('font', 'Arial Black')
      onChange('font_size', 88)
      onChange('color', '#FFFFFF')
      onChange('position', 'middle')
      onChange('outline_width', 8)
      onChange('outline_color', '#000000')
      onChange('background_style', 'none')
      onChange('background_color', '#000000')
      onChange('background_opacity', 0.7)
      if (!hideWordsPerCaption) onChange('words_per_caption', 3)
      onChange('uppercase', true)
      onChange('highlight', true)
      onChange('highlight_color', '#FFE600')
      if (!hideSecondSpeaker) {
        onChange('second_speaker', false)
        onChange('second_speaker_color', '#5CE1FF')
      }
    } else if (preset === 'conversation') {
      onChange('font', 'Trebuchet MS')
      onChange('font_size', 72)
      onChange('color', '#FFFFFF')
      onChange('position', 'bottom')
      onChange('outline_width', 4)
      onChange('outline_color', '#000000')
      onChange('background_style', 'box')
      onChange('background_color', '#111115')
      onChange('background_opacity', 0.76)
      if (!hideWordsPerCaption) onChange('words_per_caption', 3)
      onChange('uppercase', false)
      onChange('highlight', false)
      onChange('highlight_color', '#FFE600')
      if (!hideSecondSpeaker) {
        onChange('second_speaker', true)
        onChange('second_speaker_color', '#A78BFA')
      }
    }
  }
  return (
    <>
      <div>
        <label htmlFor={`${idPrefix}-preset`} className="label">Caption template</label>
        <select
          id={`${idPrefix}-preset`}
          className="input mt-1"
          defaultValue=""
          onChange={(e) => applyPreset(e.target.value)}
        >
          <option value="" disabled>Choose a starting style…</option>
          <option value="clean">Clean</option>
          <option value="karaoke">Karaoke highlight</option>
          <option value="conversation">Conversation box</option>
        </select>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2">
          <label htmlFor={`${idPrefix}-font`} className="label">
            Font
          </label>
          <select
            id={`${idPrefix}-font`}
            className="input mt-1"
            value={style.font}
            style={{ fontFamily: `'${style.font}', sans-serif` }}
            onChange={(e) => onChange('font', e.target.value)}
          >
            {CAPTION_FONTS.map((f) => (
              <option key={f} value={f} style={{ fontFamily: `'${f}', sans-serif` }}>
                {f}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor={`${idPrefix}-color`} className="label">
            Text colour
          </label>
          <input
            id={`${idPrefix}-color`}
            type="color"
            className="mt-1 h-9 w-full rounded-lg bg-raised cursor-pointer"
            value={style.color}
            onChange={(e) => onChange('color', e.target.value.toUpperCase())}
          />
        </div>
        <div>
          <label htmlFor={`${idPrefix}-size`} className="label">
            Size ({style.font_size})
          </label>
          <input
            id={`${idPrefix}-size`}
            type="range"
            min={40}
            max={140}
            className="mt-3 w-full accent-control"
            value={style.font_size}
            onChange={(e) => onChange('font_size', Number(e.target.value))}
          />
        </div>
        <div>
          <label htmlFor={`${idPrefix}-pos`} className="label">
            Position
          </label>
          <select
            id={`${idPrefix}-pos`}
            className="input mt-1"
            value={style.position}
            onChange={(e) => onChange('position', e.target.value as CaptionStyle['position'])}
          >
            <option value="bottom">Bottom</option>
            <option value="middle">Middle</option>
            <option value="top">Top</option>
          </select>
        </div>
        <div>
          <label htmlFor={`${idPrefix}-outline`} className="label">Outline ({style.outline_width}px)</label>
          <input
            id={`${idPrefix}-outline`}
            type="range"
            min={0}
            max={16}
            className="mt-3 w-full accent-control"
            value={style.outline_width}
            onChange={(e) => onChange('outline_width', Number(e.target.value))}
          />
        </div>
        <div>
          <label htmlFor={`${idPrefix}-outline-color`} className="label">Outline colour</label>
          <input
            id={`${idPrefix}-outline-color`}
            type="color"
            className="mt-1 h-9 w-full rounded-lg bg-raised cursor-pointer"
            value={style.outline_color}
            onChange={(e) => onChange('outline_color', e.target.value.toUpperCase())}
          />
        </div>
        <div>
          <label htmlFor={`${idPrefix}-background`} className="label">Background</label>
          <select
            id={`${idPrefix}-background`}
            className="input mt-1"
            value={style.background_style}
            onChange={(e) => onChange('background_style', e.target.value as CaptionStyle['background_style'])}
          >
            <option value="none">None</option>
            <option value="box">Caption box</option>
          </select>
        </div>
        {style.background_style === 'box' && (
          <>
            <div>
              <label htmlFor={`${idPrefix}-background-color`} className="label">Box colour</label>
              <input
                id={`${idPrefix}-background-color`}
                type="color"
                className="mt-1 h-9 w-full rounded-lg bg-raised cursor-pointer"
                value={style.background_color}
                onChange={(e) => onChange('background_color', e.target.value.toUpperCase())}
              />
            </div>
            <div>
              <label htmlFor={`${idPrefix}-background-opacity`} className="label">
                Box opacity ({Math.round(style.background_opacity * 100)}%)
              </label>
              <input
                id={`${idPrefix}-background-opacity`}
                type="range"
                min={0.1}
                max={1}
                step={0.05}
                className="mt-3 w-full accent-control"
                value={style.background_opacity}
                onChange={(e) => onChange('background_opacity', Number(e.target.value))}
              />
            </div>
          </>
        )}
        {!hideWordsPerCaption && (
          <div>
            <label htmlFor={`${idPrefix}-words`} className="label">
              Words per caption
            </label>
            <select
              id={`${idPrefix}-words`}
              className="input mt-1"
              value={style.words_per_caption}
              onChange={(e) => onChange('words_per_caption', Number(e.target.value))}
            >
              {[1, 2, 3, 4, 5, 6].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
      <label className="flex items-center gap-2 cursor-pointer text-sm">
        <input
          type="checkbox"
          className="size-4 accent-control"
          checked={style.uppercase}
          onChange={(e) => onChange('uppercase', e.target.checked)}
        />
        UPPERCASE captions
      </label>

      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2 cursor-pointer text-sm">
          <input
            type="checkbox"
            className="size-4 accent-control"
            checked={style.highlight}
            onChange={(e) => onChange('highlight', e.target.checked)}
          />
          Highlight each word as it&apos;s said
        </label>
        {style.highlight && (
          <input
            type="color"
            aria-label={t('Highlight colour')}
            className="h-7 w-10 rounded-md bg-raised cursor-pointer shrink-0"
            value={style.highlight_color}
            onChange={(e) => onChange('highlight_color', e.target.value.toUpperCase())}
          />
        )}
      </div>

      {!hideSecondSpeaker && (
        <div className="flex items-center gap-3">
          <label
            className="flex items-center gap-2 cursor-pointer text-sm"
            title={t(
              "When two people talk in a clip, the main speaker keeps the text colour and the other person's captions take this one. A clip with one voice looks the same as always."
            )}
          >
            <input
              type="checkbox"
              className="size-4 accent-control"
              checked={style.second_speaker}
              onChange={(e) => onChange('second_speaker', e.target.checked)}
            />
            Second speaker in another colour
          </label>
          {style.second_speaker && (
            <input
              type="color"
              aria-label={t("Second speaker's colour")}
              className="h-7 w-10 rounded-md bg-raised cursor-pointer shrink-0"
              value={style.second_speaker_color}
              onChange={(e) => onChange('second_speaker_color', e.target.value.toUpperCase())}
            />
          )}
        </div>
      )}

      <div>
        <p className="label mb-1">Example</p>
        <CaptionExample style={style} />
      </div>
    </>
  )
}
