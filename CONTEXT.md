# Widget Census

This context describes evidence about custom Jupyter widget packages and the repositories associated with them.

## Language

**Widget package**:
A Python distribution whose published source contains a recognized custom widget implementation signal.
_Avoid_: Widget, project, repository

**Package candidate**:
A discovered Python distribution awaiting or carrying source-based classification. Inclusion is evidence-backed but may still require scope review.
_Avoid_: Confirmed widget

**Implementation signal**:
A recognized source pattern for an anywidget or traditional custom-widget implementation. A signal is positive evidence, not proof that other implementations are absent.
_Avoid_: Implementation type

**Observed-by date**:
The upload date of the earliest inspected release artifact containing a signal. It is an upper bound on when the implementation existed.
_Avoid_: Creation date, invention date

**Port candidate**:
A widget package with a traditional signal in an earlier inspected release and an anywidget signal in a later release. Component continuity requires review.
_Avoid_: Ported package

**Repository identity**:
The canonical GitHub repository resolved from package and discovery metadata. Multiple widget packages may share one repository.
_Avoid_: Widget package

**Legacy inventory**:
The preserved repository-level dataset maintained by the earlier Deno workflow. It is an input and comparison baseline, not the current census unit.
_Avoid_: Current census
