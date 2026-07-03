import { useRef, useState } from 'react'
import { UploadCloud, FileCheck2 } from 'lucide-react'

export default function DropZone({ accept, hint, file, onFile }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  const handleFiles = (files) => {
    if (files && files[0]) onFile(files[0])
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        handleFiles(e.dataTransfer.files)
      }}
      className={`rounded-card border-2 border-dashed px-6 py-8 text-center cursor-pointer transition-colors ${
        dragging
          ? 'border-primary bg-primary/10'
          : file
            ? 'border-success/50 bg-success/5'
            : 'border-border hover:border-primary/50 bg-bg'
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      {file ? (
        <>
          <FileCheck2 size={26} className="text-success mx-auto" />
          <p className="text-sm text-text mt-2 font-medium">{file.name}</p>
          <p className="text-xs text-text-dim mt-1">Click to choose a different file</p>
        </>
      ) : (
        <>
          <UploadCloud size={26} className="text-text-dim mx-auto" />
          <p className="text-sm text-text mt-2">
            Drag &amp; drop or <span className="text-primary font-medium">browse</span>
          </p>
          {hint && <p className="text-xs text-text-dim mt-1">{hint}</p>}
        </>
      )}
    </div>
  )
}
