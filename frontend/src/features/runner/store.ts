import { create } from 'zustand';

interface RunnerState {
  issueKey: string;
  selectedTemplateId: string | null;
  selectedTemplateName: string | null;
  instructions: string; // this text becomes TASK_INSTRUCTIONS on the server
  instructionsBaseline: string; // the template text as loaded, to detect edits
  output: string;
  outputDirty: boolean;
  detailTemplateId: string | null; // drives the details modal

  setIssueKey: (v: string) => void;
  useTemplate: (id: string, name: string, instructions: string) => void;
  setInstructions: (v: string) => void;
  setOutput: (v: string) => void; // from a run result (not user-dirty)
  editOutput: (v: string) => void; // user edits in the output editor
  openDetail: (id: string) => void;
  closeDetail: () => void;
}

export const useRunnerStore = create<RunnerState>((set) => ({
  issueKey: '',
  selectedTemplateId: null,
  selectedTemplateName: null,
  instructions: '',
  instructionsBaseline: '',
  output: '',
  outputDirty: false,
  detailTemplateId: null,

  setIssueKey: (issueKey) => set({ issueKey }),
  useTemplate: (id, name, instructions) =>
    set({
      selectedTemplateId: id,
      selectedTemplateName: name,
      instructions,
      instructionsBaseline: instructions,
      detailTemplateId: null,
    }),
  setInstructions: (instructions) => set({ instructions }),
  setOutput: (output) => set({ output, outputDirty: false }),
  editOutput: (output) => set({ output, outputDirty: true }),
  openDetail: (detailTemplateId) => set({ detailTemplateId }),
  closeDetail: () => set({ detailTemplateId: null }),
}));
