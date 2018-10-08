import React from "react";
import PropTypes from "prop-types";

import ExtensionContext from "./Context/ExtensionContext";
import { ObjectPreview } from "./Objects/ObjectPreview";
import { PreviewProvider } from "./Context/PreviewProvider";
import { TaskInstance } from "./TasksView";

import { Divider, Message, Segment, Menu, Select, Input, Button } from "semantic-ui-react";
import { DocumentContext, EditableDocProvider } from "./Context/DocumentContext";
import { ObjectProperties } from "./Objects/ObjectProperties";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


class ActionEditor extends React.Component {

    constructor (props) {
        super(props);
        this.state = {
            action: '',
            name: ''
        }
    }

    render () {
        return (
            <ExtensionContext.Consumer>
                {({ extension, send }) => {
                    const { action, name } = this.state;
                    const { exports } = extension;
                    const actionChoices = exports ? Object.keys(exports).map(exp => ({ text: exp, value: exp })) : [];
                    const schemas = exports && action ? { [action]: exports[action].schema } : {};

                    return (
                        <React.Fragment>
                            <Select
                                fluid
                                placeholder={'Select an action'}
                                options={actionChoices}
                                value={action}
                                onChange={(e, { value }) => this.setState({ action: value })}
                            />

                            {action &&
                                <React.Fragment>
                                    <EditableDocProvider
                                        type={action}
                                        schemas={schemas}
                                        onSave={doc => send({ action, context: doc, name })}
                                    >
                                        <ObjectProperties as={'div'} style={{ marginTop: '2em' }}/>

                                        <DocumentContext.Consumer>
                                            {({ save }) => (
                                                <Input
                                                    placeholder={'Task name'}
                                                    icon={'font'}
                                                    iconPosition={'left'}
                                                    fluid
                                                    value={name}
                                                    onChange={(e, { value }) => this.setState({ name: value })}
                                                    action={<Button icon={'send'} onClick={save}/>}
                                                />
                                            )}
                                        </DocumentContext.Consumer>
                                    </EditableDocProvider>
                                </React.Fragment>
                            }
                        </React.Fragment>
                    )
                }}
            </ExtensionContext.Consumer>
        )
    }
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export default function ExtensionActions (props) {
    const { presets, editor } = props;

    return (
        <ExtensionContext.Consumer>
            { (ext) => {
                return (
                    <Segment raised>

                        <PreviewProvider type={'Extension'} id={ext.extension ? ext.extension.id : undefined}>
                            <ObjectPreview
                                small
                                style={{ paddingTop: '1em', paddingBottom: 0 }}
                            />
                        </PreviewProvider>

                        <Divider/>

                        {presets &&
                            <Menu vertical fluid text>
                                <Menu.Item header>Presets</Menu.Item>
                                {presets.map(preset => (
                                    <Menu.Item key={preset.action} content={preset.name} onClick={() => ext.send(preset)}/>
                                ))}
                                {editor && <Menu.Item header style={{ marginTop: '2em'}}>Create</Menu.Item>}
                            </Menu>
                        }

                        {editor && <ActionEditor/>}

                        {ext.errors.length
                            ? <React.Fragment>
                                <Divider/>
                                {ext.errors.map((error, idx) => (
                                    <Message key={error} error content={error} onDismiss={() => ext.dismissError(idx)}/>
                                ))}
                            </React.Fragment>
                            : <React.Fragment/>
                        }

                        {ext.instances.length
                            ? <React.Fragment>
                                <Divider/>
                                {ext.instances.map((instanceId, idx) => (
                                    <TaskInstance key={instanceId} instanceId={instanceId} onClose={() => ext.closeTracker(instanceId)}/>
                                ))}
                            </React.Fragment>
                            : <React.Fragment/>
                        }

                    </Segment>
                )
            }}
        </ExtensionContext.Consumer>
    )
}


ExtensionActions.propTypes = {
    presets: PropTypes.arrayOf(PropTypes.object),
    editor: PropTypes.bool,
};


ExtensionActions.defaultProps = {
    presets: [],
    editor: false
};


