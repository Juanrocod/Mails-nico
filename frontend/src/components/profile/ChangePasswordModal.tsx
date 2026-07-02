import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { changePassword } from "../../services/auth";

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function ChangePasswordModal({ open, onClose }: Props) {
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  function reset() {
    setOldPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setError("");
    setSuccess(false);
  }

  function handleClose() {
    reset();
    onClose();
  }

  function validatePassword(p: string): string | null {
    if (p.length < 8) return "La contraseña debe tener al menos 8 caracteres";
    if (!/[A-Z]/.test(p)) return "La contraseña debe tener al menos una mayúscula";
    if (!/[0-9]/.test(p)) return "La contraseña debe tener al menos un número";
    if (!/[^a-zA-Z0-9]/.test(p)) return "La contraseña debe tener al menos un carácter especial (!@#$...)";
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const pwError = validatePassword(newPassword);
    if (pwError) {
      setError(pwError);
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Las contraseñas nuevas no coinciden");
      return;
    }
    setLoading(true);
    try {
      await changePassword(oldPassword, newPassword);
      setSuccess(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al cambiar la contraseña");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) handleClose(); }}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Cambiar contraseña</DialogTitle>
        </DialogHeader>

        {success ? (
          <div className="space-y-4">
            <p className="text-sm text-success-text bg-success/15 rounded-md px-3 py-2">
              Contraseña actualizada correctamente.
            </p>
            <Button className="w-full" onClick={handleClose}>
              Cerrar
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Contraseña actual</label>
              <Input
                type="password"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Nueva contraseña</label>
              <Input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="mínimo 8 caracteres"
                required
                autoComplete="new-password"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Mínimo 8 caracteres, una mayúscula, un número y un carácter especial (!@#$...).
              </p>
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Confirmar nueva contraseña</label>
              <Input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>
            {error && <p className="text-xs text-destructive">{error}</p>}
            <div className="flex gap-2 pt-1">
              <Button type="button" variant="outline" className="flex-1" onClick={handleClose} disabled={loading}>
                Cancelar
              </Button>
              <Button type="submit" className="flex-1" disabled={loading}>
                {loading ? "Guardando..." : "Guardar"}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
