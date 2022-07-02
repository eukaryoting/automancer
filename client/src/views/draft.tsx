import * as React from 'react';

import type { Host, Route } from '../application';
import { Icon } from '../components/icon';
import { DraftOverview } from '../components/draft-overview';
import { TextEditor } from '../components/text-editor';
import { VisualEditor } from '../components/visual-editor';
import { Draft, DraftPrimitive } from '../draft';
import * as util from '../util';
import { Pool } from '../util';
import { BarNav } from '../components/bar-nav';


export type ViewDraftMode = 'overview' | 'text' | 'visual';

export interface ViewDraftProps {
  draft: Draft;
  host: Host;
  mode: ViewDraftMode;
  setDraft(draft: DraftPrimitive): Promise<void>;
  setRoute(route: Route): void;
}

export interface ViewDraftState {

}

export class ViewDraft extends React.Component<ViewDraftProps, ViewDraftState> {
  pool = new Pool();

  constructor(props: ViewDraftProps) {
    super(props);
  }

  render() {
    let component = (() => {
      switch (this.props.mode) {
        case 'overview': return (
          <DraftOverview
            draft={this.props.draft}
            host={this.props.host} />
        );

        case 'text': return (
          <TextEditor
            draft={this.props.draft}
            onSave={(source) => {
              this.pool.add(async () => {
                await this.props.setDraft({
                  id: this.props.draft.id,
                  source
                });
              });
            }} />
        );

        case 'visual': return (
          <VisualEditor
            draft={this.props.draft} />
        );
      }
    })();

    return (
      <main className="blayout-container">
        <header className="blayout-header">
          <h1>{this.props.draft.entry?.name ?? '[Untitled]'}</h1>
          <BarNav
            entries={[
              { id: 'overview',
                label: 'Overview',
                icon: 'hexagon' },
              { id: 'text',
                label: 'Text editor',
                icon: 'code' },
              { id: 'visual',
                label: 'Visual editor',
                icon: 'imagesearch_roller' }
            ]}
            selectEntry={(mode) => {
              this.props.setRoute(['protocol', this.props.draft.id, mode]);
            }}
            selectedEntryId={this.props.mode} />
        </header>

        {component}
      </main>
    );
  }
}