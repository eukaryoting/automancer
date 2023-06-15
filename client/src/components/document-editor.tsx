import * as React from 'react';

import viewStyles from '../../styles/components/view.module.scss';

import { DocumentItem } from '../views/draft';
import * as util from '../util';
import { Button } from './button';
import { Pool } from '../util';
import { TextEditor } from './text-editor';
import { HostDraftCompilerResult } from '../interfaces/draft';


export interface DocumentEditorProps {
  documentItem: DocumentItem;
  getCompilation(): Promise<HostDraftCompilerResult>;
}

export interface DocumentEditorState {

}

export class DocumentEditor extends React.Component<DocumentEditorProps, DocumentEditorState> {
  pool = new Pool();

  constructor(props: DocumentEditorProps) {
    super(props);

    this.state = {};
  }

  render() {
    return (
      <>
        {!this.props.documentItem.snapshot.readable && (
          <div className={util.formatClass(viewStyles.blankOuter)}>
            <div className={viewStyles.blankInner}>
              <p>Please grant read and write permissions on this file to continue.</p>

              <div className={viewStyles.blankActions}>
                <Button onClick={() => {
                  this.pool.add(async () => {
                    await this.props.documentItem.snapshot.model.request!();
                  });
                }}>Open protocol</Button>
              </div>
            </div>
          </div>
        )}
        {this.props.documentItem.model && (
          <TextEditor
            autoSave={false}
            documentItem={this.props.documentItem}
            getCompilation={this.props.getCompilation} />
        )}
      </>
    );
  }
}
