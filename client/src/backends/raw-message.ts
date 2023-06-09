import { BackendCommon, ChipId, ProtocolLocation } from './common';
import type { DraftCompilation, DraftId } from '../draft';
import type { Codes, UnitNamespace } from '../units';
import type { ProtocolBlockPath } from '../interfaces/protocol';
import type { HostDraft, HostDraftCompilerOptions } from '../interfaces/draft';


export abstract class RawMessageBackend extends BackendCommon {
  protected abstract _request(request: unknown): Promise<unknown>;


  async command<T>(options: { chipId: ChipId; command: T; namespace: UnitNamespace; }) {
    await this._request({
      type: 'command',
      chipId: options.chipId,
      command: options.command,
      namespace: options.namespace
    });
  }

  async compileDraft(options: {
    draft: HostDraft;
    options: HostDraftCompilerOptions;
  }) {
    // console.log('[FS] Compile');

    return await this._request({
      type: 'compileDraft',
      draft: options.draft,
      options: options.options
    }) as DraftCompilation;
  }

  async createChip() {
    return await this._request({
      type: 'createChip'
    }) as { chipId: ChipId; };
  }

  async createDraftSample() {
    return await this._request({
      type: 'createDraftSample'
    }) as string;
  }

  async deleteChip(chipId: ChipId, options: { trash: boolean; }) {
    await this._request({
      type: 'deleteChip',
      chipId,
      trash: options.trash
    });
  }

  async duplicateChip(chipId: ChipId, options: { template: boolean; }) {
    return await this._request({
      type: 'duplicateChip',
      chipId,
      template: options.template
    }) as { chipId: ChipId; };
  }

  async instruct<T>(instruction: T) {
    await this._request({
      type: 'instruct',
      instruction
    });
  }

  async pause(chipId: string, options: { neutral: boolean; }) {
    await this._request({
      type: 'pause',
      chipId,
      options
    });
  }

  async reloadUnits() {
    await this._request({
      type: 'reloadUnits'
    });
  }

  async resume(chipId: string) {
    await this._request({
      type: 'resume',
      chipId
    });
  }

  async revealChipDirectory(chipId: string) {
    await this._request({
      type: 'revealChipDirectory',
      chipId
    });
  }

  async sendMessageToActiveBlock(chipId: ChipId, path: ProtocolBlockPath, message: unknown) {
    await this._request({
      type: 'sendMessageToActiveBlock',
      chipId,
      message,
      path
    });
  }

  async setChipMetadata(chipId: string, value: Partial<{ description: string | null; name: string; }>) {
    await this._request({
      type: 'setChipMetadata',
      chipId,
      value
    });
  }

  async setLocation(chipId: string, location: ProtocolLocation) {
    await this._request({
      type: 'setLocation',
      chipId,
      location
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

  async startDraft(options: {
    chipId: string;
    draft: HostDraft;
    options: HostDraftCompilerOptions;
  }) {
    await this._request({
      type: 'startDraft',
      chipId: options.chipId,
      draft: options.draft,
      options: options.options
    });
  }

  async upgradeChip(chipId: string) {
    await this._request({
      type: 'upgradeChip',
      chipId
    });
  }
}
