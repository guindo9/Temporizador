# Temporizador
Este programa es un temporizador de cuenta regresiva que puedes ajustar a tus necesidades.

copilar:
python -m nuitka ^
  --onefile ^
  --windows-console-mode=disable ^
  --lto=yes ^
  --follow-imports ^
  --enable-plugin=tk-inter ^
  --low-memory ^
  --jobs=8 ^
  --output-dir=build ^
  --windows-product-name="Apagado automatico" ^
  --windows-product-version="1.0.0.0" ^
  --windows-icon-from-ico=icon_89.ico ^
  --output-filename="Apagado automatico.exe" ^
  --include-data-dir=icono=icono ^
  "Apagado automatico.py"
