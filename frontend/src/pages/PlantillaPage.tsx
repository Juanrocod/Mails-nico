import { useEffect, useRef, useState } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { FileDropzone } from "../components/upload/FileDropzone";
import { getPlantilla, updatePlantilla, uploadLogo } from "../services/plantilla";
import type { Plantilla } from "../types/domain";

const VARIABLES = [
  "{{nombre}}",
  "{{monto}}",
  "{{localidad}}",
  "{{clave_union}}",
  "{{fecha_envio}}",
];

const DEFAULTS: Plantilla = {
  asunto: "Recordatorio de deuda",
  cuerpo_html:
    "<p>Estimado <strong>{{nombre}}</strong>,</p><p>Le informamos que registra una deuda con nuestra empresa. Quedo a disposición ante cualquier consulta.</p>",
  nombre_empresa: "",
  logo_url: null,
  color_primario: "#1a56db",
  monto_minimo: 0,
};

export default function PlantillaPage() {
  const [form, setForm] = useState<Plantilla>(DEFAULTS);
  const [status, setStatus] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function insertarVariable(variable: string) {
    const el = textareaRef.current;
    if (!el) return;
    const start = el.selectionStart ?? form.cuerpo_html.length;
    const end = el.selectionEnd ?? form.cuerpo_html.length;
    const next = form.cuerpo_html.slice(0, start) + variable + form.cuerpo_html.slice(end);
    set("cuerpo_html", next);
    requestAnimationFrame(() => {
      el.focus();
      const pos = start + variable.length;
      el.setSelectionRange(pos, pos);
    });
  }

  useEffect(() => {
    getPlantilla().then(setForm).catch(console.error);
  }, []);

  function set(field: keyof Plantilla, value: string | number | null) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSave() {
    setStatus("Guardando...");
    try {
      await updatePlantilla(form);
      setStatus("Guardado correctamente");
    } catch (e: unknown) {
      setStatus(e instanceof Error ? e.message : "Error al guardar");
    }
  }

  async function handleLogoSelect(file: File) {
    setStatus("Subiendo logo...");
    try {
      const updated = await uploadLogo(file);
      setForm(updated);
      setStatus("Logo actualizado");
    } catch (e: unknown) {
      setStatus(e instanceof Error ? e.message : "Error al subir el logo");
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Plantilla de Mail</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Asunto, cuerpo y monto mínimo de envío del recordatorio de cobro.
        </p>
      </div>

      <div className="space-y-4">
        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-foreground">Asunto</label>
          <Input value={form.asunto} onChange={(e) => set("asunto", e.target.value)} />
        </div>

        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-foreground">Cuerpo HTML</label>
          <div className="flex flex-wrap gap-1.5">
            {VARIABLES.map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => insertarVariable(v)}
                className="px-2 py-1 text-xs font-mono bg-secondary hover:bg-secondary/70 text-secondary-foreground rounded border border-border transition-colors"
              >
                {v}
              </button>
            ))}
          </div>
          <Textarea
            ref={textareaRef}
            rows={8}
            value={form.cuerpo_html}
            onChange={(e) => set("cuerpo_html", e.target.value)}
            className="font-mono text-sm"
          />
        </div>

        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-foreground">Nombre empresa</label>
          <Input
            value={form.nombre_empresa}
            onChange={(e) => set("nombre_empresa", e.target.value)}
          />
        </div>

        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-foreground">Logo</label>
          {form.logo_url && (
            <img
              src={form.logo_url}
              alt="Logo actual"
              className="h-12 max-w-[200px] object-contain rounded border border-border bg-secondary/30 p-2"
            />
          )}
          <FileDropzone
            file={null}
            onSelect={handleLogoSelect}
            accept="image/png,image/jpeg,image/webp"
            hint="PNG, JPG o WEBP — máximo 2MB"
          />
        </div>

        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-foreground">Color primario (hex)</label>
          <div className="flex gap-2 items-center">
            <input
              type="color"
              value={form.color_primario}
              onChange={(e) => set("color_primario", e.target.value)}
              className="h-9 w-9 rounded border border-border"
            />
            <Input
              value={form.color_primario}
              onChange={(e) => set("color_primario", e.target.value)}
              className="w-32"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-foreground">
            Monto mínimo de envío ($)
          </label>
          <Input
            type="number"
            value={form.monto_minimo}
            onChange={(e) => set("monto_minimo", Number(e.target.value))}
            className="w-40"
          />
        </div>

        {status && <p className="text-sm text-muted-foreground">{status}</p>}
        <Button onClick={handleSave}>Guardar plantilla</Button>
      </div>
    </div>
  );
}
