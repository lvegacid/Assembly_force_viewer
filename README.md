# Assembly Force Viewer

Herramientas para analizar fuerzas/torques por step de montaje y visualizar resultados.

## Contenido

- `Assembly_viewer_gui.py`: GUI para navegar Steps, ver plots, tablas y worst cases.
- `Force_extractor_assembly.py`: genera tablas, plots y worst cases desde `Fuerzas.txt`.
- `Assembly_ForcesExtractorFromComsol.m`: script MATLAB para extracción desde COMSOL.

## Requisitos

- Python 3.9+
- Paquetes Python:
  - numpy
  - pandas
  - matplotlib
  - PyQt5

Instalación rápida:

```bash
pip install numpy pandas matplotlib pyqt5
```

## Uso de la GUI

```bash
python Assembly_viewer_gui.py
```

### Flujo recomendado

1. Seleccionar `System` en el desplegable.
2. Si no existe el path, elegir carpeta nueva y guardar.
3. Pulsar `Run Force Assembly Analysis`.
4. Elegir si incluir Lids (`Include Lids?`).
5. Revisar resultados por Step en la GUI.

## Uso directo del extractor

```bash
python Force_extractor_assembly.py --base_folder "RUTA" --magnet_info "NOMBRE_SISTEMA"
```

Con Lids:

```bash
python Force_extractor_assembly.py --base_folder "RUTA" --magnet_info "NOMBRE_SISTEMA" --include_lids
```

## Salidas principales

Por cada `Step*`:
- `StepX_Fx.png`, `StepX_Fy.png`, ..., `StepX_NormT.png`
- `StepX_TableForceTorqueSum_perRing.txt`
- (opcional Lids) `StepX_*_Lids.png`, `StepX_TableForceTorqueSum_perLid.txt`

Global:
- `WorstCases_Global.txt`

## Notas

- La escala signed de `Fx/Fy/Fz/Tx/Ty/Tz` está fijada por componente usando worst case global de todos los Steps.
- `NormF` y `NormT` mantienen escala propia por plot.
