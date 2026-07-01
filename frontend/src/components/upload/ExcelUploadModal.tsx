import { useRef, useState } from 'react'
import { Upload } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'
import { Button } from '../ui/button'
import { cn } from '../../lib/utils'

interface Props {
  open: boolean
  onClose: () => void
}

export default function ExcelUploadModal({ open, onClose }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)

  function reset() {
    setFile(null)
  }

  function handleClose() {
    reset()
    onClose()
  }

  function selectFile(f: File) {
    if (!f.name.match(/\.(xlsx|xls)$/i)) {
      return
    }
    setFile(f)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Subir archivo Excel</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div
            onDragOver={(e) => {
              e.preventDefault()
              setIsDragOver(true)
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={(e) => {
              e.preventDefault()
              setIsDragOver(false)
              const f = e.dataTransfer.files[0]
              if (f) selectFile(f)
            }}
            className={cn(
              'border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors',
              isDragOver ? 'border-blue-500 bg-blue-50' : 'border-slate-300 hover:border-slate-400'
            )}
          >
            <Upload className="h-8 w-8 mx-auto text-slate-400 mb-2" />
            <p className="text-sm font-medium text-slate-700">Arrastra un archivo aquí</p>
            <p className="text-xs text-slate-500 mt-1">o haz clic para seleccionar</p>
            <input
              ref={inputRef}
              type="file"
              accept=".xlsx,.xls"
              onChange={(e) => {
                const f = e.currentTarget.files?.[0]
                if (f) selectFile(f)
              }}
              className="hidden"
            />
          </div>
          {file && <p className="text-sm text-slate-600">Archivo: {file.name}</p>}
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={handleClose}>
              Cancelar
            </Button>
            <Button onClick={() => {}}>
              Subir
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
