import { useState } from 'react'
import { ClipboardPaste, Eye, EyeOff } from 'lucide-react'
import { useStudio } from './StudioContext'

interface Props {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  id?: string
  onEnter?: () => void
}

/** A key box that is easy to paste into: show/hide, and a Paste button for browsers that block Cmd/Ctrl+V on password fields. */
export function KeyInput({ value, onChange, placeholder = 'Paste your key here', id, onEnter }: Props) {
  const { notify } = useStudio()
  const [show, setShow] = useState(false)

  const paste = async () => {
    try {
      const text = (await navigator.clipboard.readText()).trim()
      if (text) onChange(text)
      else notify('The clipboard is empty. Copy your key first.', 'error')
    } catch {
      notify('Your browser would not let the page read the clipboard. Click in the box and press Cmd+V (Ctrl+V on Windows) instead.', 'error')
    }
  }

  return (
    <div className="key-input">
      <input id={id} type={show ? 'text' : 'password'} autoComplete="off" spellCheck={false} placeholder={placeholder} value={value}
        onChange={e => onChange(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && onEnter) onEnter() }} />
      <button type="button" className="btn-secondary small" onClick={paste} title="Paste from your clipboard"><ClipboardPaste size={13} /> Paste</button>
      <button type="button" className="icon-btn" onClick={() => setShow(v => !v)} aria-label={show ? 'Hide the key' : 'Show the key'}>{show ? <EyeOff size={15} /> : <Eye size={15} />}</button>
    </div>
  )
}
