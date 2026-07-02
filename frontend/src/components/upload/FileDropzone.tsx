import { useRef, useState } from "react";
import { FileSpreadsheet } from "lucide-react";
import { cn } from "../../lib/utils";

interface Props {
  file: File | null;
  onSelect: (file: File) => void;
  disabled?: boolean;
}

export function FileDropzone({ file, onSelect, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) onSelect(f);
    e.target.value = "";
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;
    const dropped = e.dataTransfer.files[0];
    if (dropped) onSelect(dropped);
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept=".xlsx,.xls"
        className="hidden"
        onChange={handleChange}
        disabled={disabled}
      />
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => {
          if (!disabled && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        className={cn(
          "border-2 border-dashed rounded-lg p-10 text-center transition-colors",
          disabled ? "opacity-60 pointer-events-none" : "cursor-pointer",
          isDragOver
            ? "border-primary bg-secondary/60"
            : "border-border hover:border-muted-foreground/40 hover:bg-secondary/40"
        )}
      >
        <FileSpreadsheet className="h-8 w-8 mx-auto text-muted-foreground/60 mb-3" />
        <p className="text-sm font-medium text-foreground">
          {file ? file.name : "Arrastrá el archivo o hacé click para seleccionar"}
        </p>
        <p className="text-xs text-muted-foreground mt-1">Solo .xlsx o .xls</p>
      </div>
    </>
  );
}
