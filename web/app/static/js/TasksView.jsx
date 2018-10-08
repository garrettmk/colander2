import React from "react";
import PropTypes from "prop-types";

import { Container, Progress, Segment, Table, Popup, List, Icon, Button, Header, Divider,
    Loader, Grid, Modal, Label } from "semantic-ui-react";
import Colander from "./colander";
import ExtensionContext from "./Context/ExtensionContext";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export class TaskInstance extends React.Component {

    constructor (props) {
        super(props);

        this.fetchTaskInstance = this.fetchTaskInstance.bind(this);

        this.state = {
            loading: false,
            instance: {},
            intervalId: undefined,
            message: undefined
        }
    }

    componentDidMount () {
        this.fetchTaskInstance();
        const intervalId = setInterval(this.fetchTaskInstance, 1000);
        this.setState({ intervalId });
    }

    componentWillUnmount () {
        clearInterval(this.state.intervalId);
    }

    fetchTaskInstance () {
        const { instanceId } = this.props;
        if (!instanceId)
            return;

        Colander.filter('TaskInstance', {
            query: { id: instanceId },

            onSuccess: results => this.setState({
                loading: false,
                instance: results.items[0],
                message: undefined
            }),

            onFailure: error => this.setState({ message: error })
        })
    }

    render () {
        const { onClose } = this.props;
        const {
            instance: {
                progress = [],
                errors = [],
                counts = {},
                context_id,
                data = {}
            }
        } = this.state;

        const progressString = `${progress[0]}/${progress[1]}`;
        const totalActors = Object.values(counts).reduce((sum, cnt) => sum + cnt, 0);
        const totalErrors = Object.keys(errors).length;

        const styles = {
            topRow: {
                display: 'flex',
                flexdirection: 'row',
                flexWrap: 'nowrap',
                alignItems: 'center',
                width: '100%'
            },
            progress: {
                margin: 0,
                padding: 0,
                width: '100%'
            },
            header: {
                width: '100%',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
            },
            bottomRow: {
                display: 'flex',
                flexDirection: 'row',
                alignItems: 'center',
                justifyContent: 'space-between',
                width: '100%'
            },
        };

        return (
            <Segment>
                <div style={styles.topRow}>
                    <Icon name={'cogs'} size={'big'} style={{ marginRight: '10px' }}/>
                    <Progress
                        value={progress[0]}
                        total={progress[1]}
                        progress={'percent'}
                        precision={0}
                        error={!!totalErrors}
                        indicating
                        autoSuccess
                        style={styles.progress}
                    />
                </div>
                <Header style={styles.header}>
                    {name || context_id}
                </Header>
                <div style={styles.bottomRow}>
                    <Label.Group size={'tiny'}>
                        <Label icon={'send'} content={progressString}/>
                        <TaskInstanceDataModal
                            icon={'cog'}
                            label={totalActors}
                            data={counts}
                        />
                        <TaskInstanceDataModal
                            icon={'warning'}
                            label={totalErrors}
                            color={totalErrors ? 'red' : undefined}
                            data={errors}
                        />
                    </Label.Group>
                    <Label.Group size={'tiny'}>
                        <TaskInstanceDataModal label={'{...}'} color={'grey'} data={data}/>
                        <Label as={'a'} icon={'play'} color={'blue'}/>
                        <Label as={'a'} icon={'close'} color={'red'} onClick={() => onClose()}/>
                    </Label.Group>
                </div>
            </Segment>
        )
    }
}

function TaskInstanceDataModal (props) {
    const { icon, label, data, color } = props;

    return (
        <Modal trigger={<Label as={'a'} icon={icon} content={label} color={color}/>}>
            <Modal.Header>{label}</Modal.Header>
            <Modal.Content>
                <pre>{JSON.stringify(data, null, '  ')}</pre>
            </Modal.Content>
        </Modal>
    )
}


TaskInstance.propTypes = {
    instanceId: PropTypes.number,
    onClose: PropTypes.func,
};


TaskInstance.defaultProps = {
    onClose: () => {},
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export default class TasksView extends React.Component {

    constructor (props) {
        super(props);

        this.fetchTaskInstances = this.fetchTaskInstances.bind(this);

        this.state = {
            loading: false,
            instances: [],
            intervalId: undefined
        }
    }

    componentDidMount () {
        this.fetchTaskInstances();
        this.setState({ intervalId: setInterval(this.fetchTaskInstances, 1000) });
    }

    componentWillUnmount () {
        clearInterval(this.state.intervalId);
    }

    fetchTaskInstances () {
        this.setState({ loading: true });

        Colander.filter('TaskInstance', {

            onSuccess: results => {
                this.setState({ loading: false, instances: results.items });
            },

            onFailure: error => console.log(error)
        })
    }

    closeTaskInstance(idx) {
        const { instances } = this.state;
        const instance = instances[idx];
        instances.splice(idx, 1);

        Colander.delete_('TaskInstance', {
            query: { id: instance.id }
        })
    }

    render () {
        const { loading, instances } = this.state;

        return (
            <ExtensionContext.Consumer>
                { ext => (
                    <Container style={{ marginTop: '5em' }}>
                        <Segment raised>
                            {instances.map((instance, idx) => (
                                <TaskInstance key={instance.id} instanceId={instance.id} onClose={() => this.closeTaskInstance(idx)}/>
                            ))}
                        </Segment>
                    </Container>
                )}
            </ExtensionContext.Consumer>
        )
    }
}