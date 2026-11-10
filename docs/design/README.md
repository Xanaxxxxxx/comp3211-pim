# PIM design diagrams

Four diagrams derived from the implemented Python source at commit `fcaee3f`. Each figure includes an English explanation. The combined PDF also includes notation, design decisions, the example scenario, and an API reference with parameter names/types, return values and expected exceptions.

## Downloads

- [Combined PDF with English explanations and API reference](PIM_Design_Diagrams.pdf)
- [Figure 1 System architecture](images/01_architecture.png)
- [Figure 2 Record and persistence classes](images/02_record_classes.png)
- [Figure 3 Search and control classes](images/03_search_control_classes.png)
- [Figure 4 Search then update sequence](images/04_search_update_sequence.png)
- [English explanations in editable Markdown](DESIGN_EXPLANATIONS.md)

The first four PDF pages are vector diagrams on landscape A3 pages. The remaining pages are the English design notes and API reference on landscape A4. PNGs are rendered from the corresponding PDF pages at 2 pixels per PDF point (approximately 2382 by 1684 pixels). Use the PDF for sharp printing or zooming and the PNGs for inserting into documents or slides.

## Reading the diagrams

Figure 1 instantiates an MVC-style architecture using the actual entry point, controller, view and model modules. Figure 2 shows record inheritance and PIM collection ownership, together with validation/persistence functions. Figure 3 shows the parser, recursive criterion references, Controller and CommandResult. Figure 4 follows an existing task through search and a subsequent update by ID.

The figures deliberately distinguish source classes from documentation shorthand: Criterion abbreviates Predicate, Negation or Junction; no common superclass or interface exists in the source. Types marked inferred describe unannotated Python returns. A time-field constructor/update accepts either ISO 8601 text or datetime and stores a normalized datetime. The example updates memory only; an explicit save is needed to persist it.

## Rebuild

The editable generation source is [source/generate_diagrams.py](source/generate_diagrams.py). It derives API signatures from the application AST and draws the four diagrams deterministically. Run it from any working directory with a documentation environment containing reportlab, pypdf and pypdfium2:

```sh
python docs/design/source/generate_diagrams.py
```

This script is optional documentation tooling. These packages are not used by the PIM application, its model, or its tests; those continue to use the Python standard library only. The script writes the PDF, four PNGs and English explanation Markdown under this directory.

OpenAI Codex assisted in preparing these diagrams and explanations. Include actual usage in the group's Honour Declaration. Integrate these materials into the group's final design document and keep its terminology consistent with the final SRS.
