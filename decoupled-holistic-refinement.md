# Implementation Plan: Decoupled Holistic Alignment & UI Refactoring

This plan implements a high-precision 543-point Holistic alignment as an optional refinement method and refactors the `RefinementPage` UI into independent, decoupled modules for each optimization technique.

## 1. Objectives
- **Decoupled Architecture**: Refactor `RefinementPage.js` to separate method configurations (MLS-33, Holistic-543, RIFE) into isolated UI modules.
- **High-Precision Option**: Add "Holistic MLS (543 pts)" as a premium alignment option for fixing subtle body lean and facial offsets.
- **State Isolation**: Ensure parameters for one method do not affect or overlap with others.
- **On-Demand Holistic Inference**: Perform 543-point extraction only when requested for a specific clip.

## 2. Key Files & Context
- `static/js/pages/RefinementPage.js`: Complete modular refactor of the UI.
- `app/services/alignment_service.py`: Decouple processing logic using a Strategy-like pattern.
- `download_models.sh`: Add Holistic model assets (`holistic_landmarker.task`).

## 3. Implementation Steps

### Phase 1: Modular Frontend Refactor
1.  **Define Method Interface**: In `RefinementPage.js`, create an object-based registry for methods:
    ```javascript
    const REFINE_METHODS = {
      mls: { label: 'Spatial (33 pts)', render: renderMLS, getParams: getMLSParams },
      holistic: { label: 'Spatial (543 pts)', render: renderHolistic, getParams: getHolisticParams },
      rife: { label: 'Temporal (RIFE)', render: renderRIFE, getParams: getRIFEParams }
    };
    ```
2.  **Dynamic Rendering**: Update the `RefinementPage` to clear and re-render only the specific settings container when a method is selected.
3.  **Holistic Visualization**: Implement a specialized renderer for the cyan Face Mesh and orange Hand landmarks that activates only in Holistic mode.

### Phase 2: Decoupled Backend Service
1.  **Strategy Implementation**: Split `AlignmentService` processing logic:
    - `process_standard_mls()`: handles 33-point warping.
    - `process_holistic_mls()`: performs holistic extraction + 543-point warping.
2.  **Holistic Task Integration**: Initialize the Holistic task model locally within the `AlignmentService`.
3.  **On-the-fly Landmarks**: Add an endpoint/method to fetch 543 points for a single frame to support frontend "preview" mode.

### Phase 3: Resource Preparation
1.  **Update `download_models.sh`**: Ensure Holistic TFLite and WASM assets are available in `static/libs`.

## 4. Verification & Testing
- **UI Cleanliness**: Verify that selecting one method hides all irrelevant settings and inputs.
- **Regression**: Ensure 33-point MLS and RIFE still work perfectly.
- **Precision Test**: Verify the "Holistic MLS" mode resolves body tilt and facial orientation drifts.
