import React from "react";
import marked from "marked";

import Colander from "./colander";
import { DocumentContext, NestedDocProvider, EditableDocProvider } from "./Context/DocumentContext";
import { ModelProvider } from "./Context/ModelProvider";
import { CollectionProvider } from "./Context/CollectionContext";
import { QueryContext, QueryProvider } from "./Context/QueryContext";
import { PreviewProvider } from "./Context/PreviewProvider";
import ObjectTable from "./Objects/ObjectTable"
import ObjectPreview from "./Objects/ObjectPreview";
import ObjectProperties from "./Objects/ObjectProperties";
import ObjectHeader from "./Objects/ObjectHeader";

import { Grid, Segment, Image, Header, Button, Message, Divider, Select, Menu } from "semantic-ui-react";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


class TaskCreator extends React.Component {

    constructor (props) {
        super(props);

        this.send = this.send.bind(this);

        this.state = {
            action: undefined,
            message: undefined,
            msgSuccess: false
        }
    }

    send (extId, params) {
        Colander.sendTask({
            ext_id: extId,
            action: this.state.action,
            params,

            onSuccess: results => this.setState({
                msgSuccess: true,
                message: `Task sent! (${results.message_id})`
            }),
            onFailure: error => this.setState({
                msgSuccess: false,
                message: error
            })
        })
    }

    render () {
        const { action, message, msgSuccess } = this.state;
        const clearMessage = () => message && this.setState({ message: undefined });

        return (
            <DocumentContext.Consumer>
                { ({ loading, doc }) => {
                    const actionChoices = doc && doc.exports
                        ? Object.keys(doc.exports).map(exp => ({ text: exp, value: exp }))
                        : [];

                    const schemas = doc && doc.exports && action
                        ? { [action]: doc.exports[action].schema }
                        : {};

                    const sendTask = params => doc && this.send(doc.id, params);

                    return (
                        <Segment raised clearing loading={loading}>

                            <PreviewProvider type={'Extension'} id={doc ? doc.id : undefined}>
                                <ObjectPreview small/>
                            </PreviewProvider>
                            { doc &&
                                <React.Fragment>
                                    <Select
                                        fluid
                                        placeholder={'Select an action'}
                                        options={actionChoices}
                                        loading={loading}
                                        value={action}
                                        onChange={(e, { value }) => this.setState({ action: value })}
                                    />

                                    {action &&
                                        <React.Fragment>
                                            <Divider/>

                                            <EditableDocProvider
                                                type={action}
                                                schemas={schemas}
                                                onSave={sendTask}
                                                onEdit={clearMessage}
                                            >
                                                <ObjectProperties as={'div'}/>

                                                <Divider/>

                                                <DocumentContext.Consumer>
                                                    {({save}) => (
                                                        <Button
                                                            icon={'check'}
                                                            floated={'right'}
                                                            content={'Send'}
                                                            onClick={save}
                                                        />
                                                    )}
                                                </DocumentContext.Consumer>

                                            </EditableDocProvider>

                                            {message &&
                                            <Message error={!msgSuccess}>{message}</Message>
                                            }
                                        </React.Fragment>
                                    }
                                </React.Fragment>
                            }
                        </Segment>
                    )
                }}
            </DocumentContext.Consumer>
        )
    }
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export function ListingDetails (props) {
    return (
        <DocumentContext.Consumer>
            { ({ doc, loading }) => {
                const bodyContent = marked.parse(doc.features || doc.description || '(no description)', {sanitize: true});

                return (
                    <Segment raised>
                        <Grid divided={'vertically'}>
                            <Grid.Row>
                                <Grid.Column width={16}>
                                    <Header>
                                        {doc && (doc.title || '(no title)')}
                                    </Header>
                                </Grid.Column>
                            </Grid.Row>
                            <Grid.Row>
                                <Grid.Column width={8}>
                                    <Image src={doc && doc.image_url} size={'large'}/>
                                </Grid.Column>
                                <Grid.Column width={8}>
                                    <div
                                        dangerouslySetInnerHTML={{ __html: bodyContent }}
                                        style={{
                                            height: '36em',
                                            overflowY: 'scroll'
                                        }}
                                    />
                                </Grid.Column>
                            </Grid.Row>
                        </Grid>
                    </Segment>
                )
            }}
        </DocumentContext.Consumer>
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export default function ObjectView (props) {
    let view = {}, column1, column2;
    let { type, id } = props.match.params;
    ({ type, id } = {
        type,
        id: parseInt(id)
    });

    switch (type) {
        case 'Vendor':
            view = { extension: { _exclude: []} };
            column1 = (
                <React.Fragment>
                    <PreviewProvider type={type} id={id}>
                        <ObjectHeader/>
                    </PreviewProvider>

                    <ObjectProperties
                        only={['name', 'url', 'image_url', 'ext_id', 'avg_shipping', 'avg_tax']}
                    />

                    <NestedDocProvider node={'extension'}>
                        <DocumentContext.Consumer>
                            { ({ doc }) => doc ? <TaskCreator/> : <React.Fragment/>}
                        </DocumentContext.Consumer>
                    </NestedDocProvider>
                </React.Fragment>
            );
            column2 = (
                <React.Fragment>
                    <QueryProvider type={'Listing'} query={{ vendor_id: id }} view={{ vendor: { _only: ['name'] } }}>
                        <QueryContext.Consumer>
                            {({ type, query, view }) => (
                                <CollectionProvider type={type} query={query} view={view}>
                                    <ObjectTable
                                        only={['sku', 'Image', 'Summary', 'price']}
                                        select
                                    />
                                </CollectionProvider>
                            )}
                        </QueryContext.Consumer>
                    </QueryProvider>
                </React.Fragment>
            );
            break;

        case 'Listing':
            view = { vendor: { _only: ['name'] } };
            column1 = (
                <React.Fragment>
                    <PreviewProvider type={type} id={id}>
                        <ObjectHeader/>
                    </PreviewProvider>

                    <ObjectProperties
                        only={['vendor_id', 'sku', 'title', 'brand', 'model', 'price', 'quantity', 'quantity_desc',
                        'rank', 'rating', 'detail_url', 'image_url']}
                    />
                </React.Fragment>
            );

            column2 = (
                <React.Fragment>
                    <ListingDetails/>
                </React.Fragment>
            )
    }

    return (
        <ModelProvider {...{ type, id, view}}>
            <Grid columns={2}>
                <Grid.Column width={4}>
                    {column1}
                </Grid.Column>
                <Grid.Column width={12}>
                    {column2}
                </Grid.Column>
            </Grid>

            <DocumentContext.Consumer>
                { ({ edits, save }) => (
                    _.isEmpty(edits)
                        ? <React.Fragment/>
                        : <Menu fixed={'bottom'}>
                            <Menu.Item>
                                <Button primary onClick={save}>Save</Button>
                            </Menu.Item>
                            <Menu.Item>
                                <Button basic>Cancel</Button>
                            </Menu.Item>
                        </Menu>
                )}
            </DocumentContext.Consumer>
        </ModelProvider>
    );
}