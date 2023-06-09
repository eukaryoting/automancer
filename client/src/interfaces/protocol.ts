import type { DraftRange } from '../draft';
import type { UnitNamespace } from './unit';


export interface Protocol {
  name: string | null;
  root: ProtocolBlock;
}

export interface ProtocolBlock {
  namespace: UnitNamespace;
  [key: string]: unknown;
}

export type ProtocolBlockPath = unknown[];

export interface ProtocolProcess {
  data: unknown;
  namespace: UnitNamespace;
}

export type ProtocolState = Record<UnitNamespace, unknown>;


export interface ProtocolBlockAggregate {
  blocks: ProtocolBlock[];
  offset: number;
  state: ProtocolState | null;
}


export interface ProtocolError {
  id: string | null;
  description: string[];
  message: string;
  references: MasterErrorReference[];
}


export interface Master {
  analysis: MasterAnalysis;
  location: unknown;
  protocol: Protocol;
}

export interface MasterAnalysis {
  errors: MasterError[];
  warnings: MasterError[];
}

export interface MasterError extends ProtocolError {
  id: string;
  date: number;
  path: ProtocolBlockPath;
}

export type MasterErrorReference = MasterErrorDocumentReference | MasterErrorFileReference;

export interface MasterErrorBaseReference {
  type: string;
  id: string | null;
  label: string | null;
}

export type MasterErrorDocumentReference = MasterErrorBaseReference & {
  type: 'document';
  documentId: string;
  ranges: DraftRange[];
}

export type MasterErrorFileReference = MasterErrorBaseReference & {
  type: 'file';
  path: string;
}

export interface MasterProcessState {
  time: number;
  [key: string]: unknown;
}

export type MasterStateLocation = Record<UnitNamespace, unknown> | null;
