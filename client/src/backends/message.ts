import type { Draft } from '../application';
import { BackendCommon, Chip, ChipId, ControlNamespace } from './common';
import type { UnitsCode } from '../units';


export abstract class MessageBackend extends BackendCommon {
  protected abstract _request(message: unknown): Promise<unknown>;

  async command(chipId: string, command: ControlNamespace.RunnerCommand) {
    await this._request({
      type: 'command',
      chipId,
      command
    });
  }

  async compileDraft(draftId: string, source: string) {
    return await this._request({
      type: 'compileDraft',
      draftId,
      source
    }) as Draft['compiled'];
  }

  async createChip(options: { modelId: string; }) {
    return await this._request({
      type: 'createChip',
      modelId: options.modelId
    }) as { chipId: ChipId; };
  }

  async deleteChip(chipId: ChipId) {
    await this._request({
      type: 'deleteChip',
      chipId
    });
  }

  async pause(chipId: string, options: { neutral: boolean; }) {
    await this._request({
      type: 'pause',
      chipId,
      options
    });
  }

  async resume(chipId: string) {
    await this._request({
      type: 'resume',
      chipId
    });
  }

  async setChipMetadata(chipId: string, value: Partial<{ description: string | null; name: string; }>): Promise<void> {
    await this._request({
      type: 'setChipMetadata',
      chipId,
      value
    });
  }

  async setMatrix(chipId: ChipId, update: Partial<Chip['matrices']>) {
    await this._request({
      type: 'setMatrix',
      chipId,
      update
    });
  }

  async skipSegment(chipId: ChipId, segmentIndex: number, processState?: object) {
    await this._request({
      type: 'skipSegment',
      chipId,
      processState: processState ?? null,
      segmentIndex
    });
  }

  async startPlan(options: { chipId: string; data: UnitsCode; source: string; }) {
    await this._request({
      type: 'startPlan',
      chipId: options.chipId,
      codes: options.data,
      source: options.source
    });
  }
}
