import { List, Set as ImSet } from 'immutable';
import * as React from 'react';

import type { Route } from '../application';
import type { Draft, DraftId } from '../draft';
import type { Host } from '../host';
import { HostInfo } from '../interfaces/host';
import * as util from '../util';
import { ContextMenuArea } from './context-menu-area';
import { BaseUrl } from '../constants';

import styles from '../../styles/components/sidebar.module.scss';


const CollapsedStorageKey = 'sidebarCollapsed';


export interface SidebarProps {
  host: Host | null;
  hostInfo: HostInfo;

  setStartup?(): void;
}

export interface SidebarState {
  collapsed: boolean;
}

export class Sidebar extends React.Component<SidebarProps, SidebarState> {
  constructor(props: SidebarProps) {
    super(props);

    let collapsed;

    try {
      collapsed = JSON.parse(window.sessionStorage[CollapsedStorageKey]);
    } catch (_err) {
      collapsed = false;
    }

    this.state = {
      collapsed
    };
  }

  render() {
    let url = navigation.currentEntry.url;

    let unitEntries = this.props.host?.units && Object.values(this.props.host.units)
      .flatMap((unit) => (unit.getGeneralTabs?.() ?? []).map((entry) => ({
        ...entry,
        id: 'unit.' + entry.id,
        route: `/unit/${unit.namespace}/${entry.id}`
      })));

    let groups: {
      id: string;
      entries: {
        id: string;
        label: string;
        icon: string;
        route: string | null;
        onClick?(): void;
      }[];
    }[] = this.props.host
      ? [
        { id: 'main',
          entries: [
            { id: 'chip',
              label: 'Experiments',
              icon: 'science',
              route: '/chip' },
            { id: 'draft',
              label: 'Protocols',
              icon: 'receipt_long',
              route: '/draft' }
        ] },
        ...(unitEntries && (unitEntries?.length > 0)
          ? [{ id: 'unit', entries: unitEntries }]
          : []),
        { id: 'last',
          entries: [
            { id: 'conf',
              label: 'Settings',
              icon: 'settings',
              route: '/settings' },
            { id: 'design',
              label: 'Design',
              icon: 'design_services',
              route: '/design' },
            ...(this.props.setStartup
                ? [{
                  id: 'startup',
                  label: 'Start menu',
                  icon: 'home',
                  route: null,
                  onClick: () => void this.props.setStartup?.()
                }]
                : [])
          ] }
      ]
      : [];

    return (
      <ContextMenuArea
        createMenu={(_event) => [
          { id: '_header', name: 'Sidebar', type: 'header' },
          ...groups.flatMap((group, groupIndex) => {
            return [
              ...group.entries.map((entry) => ({
                id: [group.id, entry.id],
                icon: entry.icon,
                name: entry.label,
                checked: true
              })),
              ...(groupIndex < (groups.length - 1)
                ? [{ id: ['_header', groupIndex], type: 'divider' as const }]
                : [])
            ];
          })
        ]}
        onSelect={() => {}}>
        <aside className={util.formatClass(styles.root, { [styles.rootCollapsed]: this.state.collapsed })}>
          <div className={styles.headerRoot}>
            {/* {(hostSettingsRecord.length > 0) && (
              <select className={styles.headerSelect} value={this.props.selectedHostSettingsId ?? ''} onChange={(event) => {
                this.props.onSelectHost(event.currentTarget.value || null);
              }}>
                {!this.props.host && <option value="">–</option>}
                {hostSettingsRecord.map((hostSettings) => (
                  <option key={hostSettings.id} value={hostSettings.id}>{hostSettings.label ?? hostSettings.id}</option>
                ))}
              </select>
            )} */}
            <div className={styles.headerValueRoot}>
              <img src={this.props.hostInfo.imageUrl!} className={styles.headerValueIcon} />
              <div className={styles.headerValueTitle}>{this.props.hostInfo.label}</div>
              <div className={styles.headerValueSubtitle}>{this.props.hostInfo.description}</div>
              <div className={styles.headerValueExpand}>
                <span className="material-symbols-sharp">unfold_more</span>
              </div>
            </div>
          </div>
          <nav className={styles.navRoot}>
            {groups.map((group) => (
              <div className={styles.navGroup} key={group.id}>
                {group.entries.map((entry) => {
                  return (
                    <a
                      href={BaseUrl + (entry.route ?? '#')}
                      className={util.formatClass(styles.navEntryRoot, {
                        '_selected': url.startsWith(BaseUrl + entry.route)
                      })}
                      key={entry.id}
                      onClick={entry.onClick && ((event) => {
                        event.preventDefault();
                        entry.onClick!();
                      })}>
                      <div className={styles.navEntryIcon}>
                        <div className="material-symbols-sharp">{entry.icon}</div>
                      </div>
                      <div className={styles.navEntryLabel}>{entry.label}</div>
                    </a>
                  );
                })}
              </div>
            ))}
          </nav>
          <div className={styles.navRoot}>
            <div className={styles.navGroup}>
              <button type="button" className={util.formatClass(styles.navEntryRoot)} onClick={() => {
                let collapsed = !this.state.collapsed;
                window.sessionStorage[CollapsedStorageKey] = JSON.stringify(collapsed);
                this.setState({ collapsed });
              }}>
                <div className={styles.navEntryIcon}>
                  <div className="material-symbols-sharp">{this.state.collapsed ? 'keyboard_double_arrow_right' : 'keyboard_double_arrow_left'}</div>
                </div>
                {/* <div className={styles.navEntryLabel}>Collapse</div> */}
              </button>
            </div>
          </div>
        </aside>
      </ContextMenuArea>
    );
  }
}


// Is 'a' a superset of 'b'
function isSuperset<T>(a: T[], b: T[]): boolean {
  if (a.length < b.length) {
    return false;
  }

  for (let index = 0; index < b.length; index += 1) {
    if (a[index] !== b[index]) {
      return false;
    }
  }

  return true;
}
