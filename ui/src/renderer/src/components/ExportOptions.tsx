export type ExportCodec = 'h264' | 'h265'
export type ExportBitrate = 'source' | '4000' | '8000' | '12000'

export default function ExportOptions({
  codec,
  bitrate,
  onCodec,
  onBitrate
}: {
  codec: ExportCodec
  bitrate: ExportBitrate
  onCodec: (value: ExportCodec) => void
  onBitrate: (value: ExportBitrate) => void
}): JSX.Element {
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <label className="inline-flex items-center gap-1.5 text-muted">
        Codec
        <select
          className="bg-raised text-ink border border-raised rounded-md px-2 py-1"
          value={codec}
          onChange={(e) => onCodec(e.target.value as ExportCodec)}
        >
          <option value="h264">H.264 · widely compatible</option>
          <option value="h265">H.265 · smaller files</option>
        </select>
      </label>
      <label className="inline-flex items-center gap-1.5 text-muted">
        Bitrate
        <select
          className="bg-raised text-ink border border-raised rounded-md px-2 py-1"
          value={bitrate}
          onChange={(e) => onBitrate(e.target.value as ExportBitrate)}
        >
          <option value="source">Source / automatic</option>
          <option value="4000">4 Mb/s</option>
          <option value="8000">8 Mb/s</option>
          <option value="12000">12 Mb/s</option>
        </select>
      </label>
      <p className="basis-full text-[10px] text-muted/70">
        {bitrate === 'source'
          ? codec === 'h265'
            ? 'H.265 exports at 6 Mb/s by default; Mac uses VideoToolbox first, then FFmpeg software encoding.'
            : 'Source quality copies the rendered H.264 file without another encode.'
          : `The selected bitrate re-encodes the export at ${Number(bitrate) / 1000} Mb/s.`}
      </p>
    </div>
  )
}
