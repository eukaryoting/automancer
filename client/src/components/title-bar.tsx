import * as React from 'react';

import { Icon } from '../components/icon';
import * as util from '../util';

import styles from '../../styles/components/title-bar.module.scss';


export interface TitleBarProps {
  subtitle?: string | null;
  subtitleVisible?: unknown;
  title: string;

  tools?: {
    id: string;
    active?: unknown;
    icon: string;
    label?: string;
    onClick?(): void;
  }[];
}

export interface TitleBarState {
  notifying: boolean;
}

export class TitleBar extends React.Component<TitleBarProps, TitleBarState> {
  lastSubtitle: string | null = null;
  notificationHideTimeout: number | null = null;
  refTitle = React.createRef<HTMLDivElement>();

  constructor(props: TitleBarProps) {
    super(props);

    this.state = {
      notifying: false
    };
  }

  componentWillUnmount() {
    if (this.notificationHideTimeout !== null) {
      clearTimeout(this.notificationHideTimeout);
    }
  }

  notify() {
    if (this.props.subtitle) {
      if (this.notificationHideTimeout !== null) {
        clearTimeout(this.notificationHideTimeout);
      }

      this.setState({ notifying: true });

      this.notificationHideTimeout = setTimeout(() => {
        this.setState({ notifying: false });
      }, 2000);
    }
  }

  render() {
    this.lastSubtitle = this.props.subtitle ?? this.lastSubtitle;

    return (
      <div className={styles.root}>
        <div className={styles.left} />
        <div className={util.formatClass(styles.titleRoot, {
          '_subtitle': this.props.subtitle,
          '_visible': (this.props.subtitleVisible || this.state.notifying)
        })} ref={this.refTitle}>
          <div className={styles.titleMain}>{this.props.title}</div>
          <div className={styles.titleSub}>{this.lastSubtitle}</div>
        </div>
        <div className={styles.right}>
          {((this.props.tools?.length ?? 0) > 0) && (
            <div className={styles.toolsRoot}>
              {this.props.tools!.map((tool) => (
                <button
                  type="button"
                  className={util.formatClass(styles.toolsItem, { '_active': tool.active })}
                  title={tool.label}
                  onClick={tool.onClick}
                  key={tool.id}>
                  <Icon name={tool.icon} style="sharp" className={styles.toolsIcon} />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }
}
