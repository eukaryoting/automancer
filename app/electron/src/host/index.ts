import { BrowserWindow, dialog } from 'electron';
import * as path from 'path';
import assert from 'assert';

import { LocalHost } from '../local-host';
import { CoreApplication } from '..';
import { Pool } from '../util';
import { rootLogger } from '../logger';
import { defer } from 'pr1-shared';
import { HostSettings } from 'pr1-library';


export class HostWindow {
  closed: Promise<void>;
  closing = false;
  localHost: LocalHost | null = null;
  window: BrowserWindow | null = null;

  private logger = rootLogger.getChild(['hostWindow', this.hostSettings.id.slice(0, 8)]);
  private pool = new Pool();

  private closingDeferred = defer<void>();

  constructor(private app: CoreApplication, private hostSettings: HostSettings) {
    this.pool.add(async () => {
      await this.closingDeferred.promise;
      this.closing = true;
    });

    this.pool.add(() => this.start());
    this.closed = this.pool.wait();

    this.logger.debug('Constructed');
  }

  private async start() {
    this.localHost = null;

    if (this.hostSettings.type === 'local') {
      this.logger.debug('Starting the corresponding local host');

      this.localHost = new LocalHost(this.app, this, this.hostSettings);

      let waitClosed = async () => {
        let err = await this.localHost!.closed;

        this.localHost = null;

        if (err) {
          dialog.showErrorBox(`Host "${this.hostSettings.label}" terminated unexpectedly with code ${err.code}`, 'See the log file for details.');
          // let { response } = await dialog.showMessageBox(this.window, {
          //   message: `Host "${this.hostSettings.label}" terminated unexpectedly`,
          //   buttons: ['Ok', 'Open log file'],
          //   title: 'Error',
          //   defaultId: 0,
          //   detail: err.code ? `Code: ${err.code}` : undefined
          // });
        }

        if (!this.closing) {
          this.closingDeferred.resolve();
          this.window?.close();
        }
      };

      if (!(await this.localHost.start())) {
        this.logger.debug('Aborting window creation');
        await waitClosed();

        return;
      }

      this.pool.add(waitClosed);
    }


    this.logger.debug('Creating the Electron window');

    this.window = new BrowserWindow({
      show: !this.app.debug,
      titleBarStyle: 'hiddenInset',
      webPreferences: {
        preload: path.join(__dirname, '../preload/index.js')
      }
    });

    this.window.maximize();

    if (!this.app.debug) {
      this.window.hide();
    }

    this.window.loadFile(path.join(__dirname, '../static/host/index.html'), { query: { hostSettingsId: this.hostSettings.id } });

    this.window.on('close', () => {
      this.closingDeferred.resolve();

      if (this.localHost) {
        this.pool.add(this.localHost.closed);
        this.localHost.close();
      }
    });
  }

  focus() {
    assert(this.window);

    if (this.window.isMinimized()) {
      this.window.restore();
    }

    this.window.focus();
  }
}
