import React from "react";
import marked from "marked";

import { Grid, Segment, Container, Image, Header, Button, Message, Divider, Select, Menu,
         Tab, Icon, Dropdown } from "semantic-ui-react";

import Colander from "./colander";
import { DocumentContext, NestedDocProvider, EditableDocProvider, ModelProvider, CollectionProvider,
         QueryContext, QueryProvider, SimilarProvider, PreviewProvider } from "./Contexts";
import { ObjectTable, ObjectPreview, ObjectProperties, ObjectHeader, ObjectImage } from "./Objects";
import { defaultImages } from "./style";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


const bottomMenuStyle = {
    borderRadius: 0,
    marginTop: 0
};


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
                                                <Message
                                                    error={!msgSuccess}
                                                >
                                                    {message}
                                                    <Button basic onClick={() => this.setState({ message: undefined })}>
                                                        <Icon name={'check'}/>
                                                        Ok
                                                    </Button>
                                                </Message>
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
                const featuresContent = marked.parse(doc.features || '(no features)', { sanitize: true });
                const descriptionContent = marked.parse(doc.description || '(no description)', {sanitize: true});
                const contentStyle = { height: '36em', overflow: 'scroll' };
                const paneStyle = { border: 'none' };

                let panes = [];

                if (doc && doc.features)
                    panes.push({
                        menuItem: 'Features',
                        render: () => (
                            <Tab.Pane style={paneStyle}>
                                <div
                                    dangerouslySetInnerHTML={{ __html: featuresContent }}
                                    style={contentStyle}
                                />
                            </Tab.Pane>
                        )
                    });

                if (doc && doc.description)
                    panes.push({
                        menuItem: 'Description',
                        render: () => (
                            <Tab.Pane style={paneStyle}>
                                <div
                                    dangerouslySetInnerHTML={{ __html: descriptionContent }}
                                    style={contentStyle}
                                />
                            </Tab.Pane>
                        )
                    });

                if (doc && doc.image_url)
                    panes.push({
                        menuItem: 'Images',
                        render: () => (
                            <Tab.Pane style={paneStyle}>
                                <Image src={doc && doc.image_url} size={'large'}/>
                            </Tab.Pane>
                        )
                    });

                return (
                    <Segment raised>
                        <Tab
                            menu={{ secondary: true, pointing: true }}
                            panes={panes}
                        />
                    </Segment>
                )
            }}
        </DocumentContext.Consumer>
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export default class ObjectView extends React.Component {

    constructor (props) {
        super(props);
        this.sendCoreAction = this.sendCoreAction.bind(this);
        this.state = { leftColumnRef: undefined }
    }

    sendCoreAction (action, params) {
        return () => {
            Colander.sendTask({
                action,
                params
            })
        }
    }

    render ()  {
        let view = {}, column1, column2, actions = () => [];
        let { type, id } = this.props.match.params;
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
                            <ObjectImage/>
                        </PreviewProvider>

                        <ObjectProperties
                            only={['name', 'url', 'image_url', 'ext_id', 'avg_shipping', 'avg_tax', 'extra']}
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

                actions = doc => [
                    <Dropdown.Item key={1} onClick={this.sendCoreAction('ImportInventory', { vendor_id: doc.id })}>
                        Import inventory
                    </Dropdown.Item>
                ];

                break;

            case 'Listing':
                view = { vendor: { _only: ['name'] } };
                column1 = (
                    <React.Fragment>
                        <PreviewProvider type={type} id={id}>
                            <ObjectImage/>
                        </PreviewProvider>

                        <ObjectProperties
                            only={['vendor_id', 'sku', 'title', 'brand', 'model', 'price', 'quantity', 'quantity_desc',
                            'rank', 'rating', 'detail_url', 'image_url', 'extra']}
                        />
                    </React.Fragment>
                );

                column2 = (
                    <React.Fragment>
                        <ListingDetails/>
                        <SimilarProvider id={id} view={{ vendor: { _only: ['name'] } }}>
                            <Segment raised>
                                <Header>
                                    Similar Listings
                                </Header>
                                <ObjectTable
                                    as={'div'}
                                    only={['Score', 'Vendor/SKU', 'Image', 'Summary', 'price']}
                                    select
                                />
                            </Segment>
                        </SimilarProvider>
                    </React.Fragment>
                );

                actions = doc => [
                    <Dropdown.Item key={1} onClick={this.sendCoreAction('ImportMatchingListings', { listing_ids: [doc.id] })}>
                        Find matching listings
                    </Dropdown.Item>,
                ];

                break;
        }

        return (
            <ModelProvider {...{ type, id, view}}>
                <DocumentContext.Consumer>
                    { ({ doc }) => (
                        <Menu inverted color='grey' style={bottomMenuStyle}>

                            <Menu.Item header>
                                <Image size={'mini'} src={defaultImages[type].dark}/>
                            </Menu.Item>

                            <Menu.Item>
                                <Header inverted as={'h2'}>
                                    {doc.name || doc.title || '(no title)'}
                                </Header>
                            </Menu.Item>

                            {(doc.url || doc.detail_url) &&
                                <Menu.Item href={doc.url || doc.detail_url} target={'_blank'}>
                                    <Icon name={'external'}/>
                                </Menu.Item>
                            }

                            {actions && (
                                <Menu.Item>
                                    <Dropdown item icon={'settings'}>
                                        <Dropdown.Menu>
                                            {actions(doc)}
                                        </Dropdown.Menu>
                                    </Dropdown>
                                </Menu.Item>
                            )}

                        </Menu>
                    )}
                </DocumentContext.Consumer>
                <Container fluid style={{ paddingLeft: '5em', paddingRight: '5em'}}>
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
            </Container>
            </ModelProvider>
        );
    }
}