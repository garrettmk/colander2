import React from "react";
import marked from "marked";
import update from "immutability-helper";

import { Grid, Segment, Container, Image, Header, Button, Message, Divider, Select, Menu,
         Tab, Icon, Dropdown } from "semantic-ui-react";

import { DocumentContext, NestedDocProvider, EditableDocProvider, ModelProvider, CollectionProvider,
         QueryContext, QueryProvider, SimilarProvider, PreviewProvider } from "./Contexts";
import { ObjectTable, ObjectPreview, ObjectProperties, ObjectHeader, ObjectImage } from "./Objects";
import { ListingActions, CoreListingActions } from "./ListingActions.jsx";
import { VendorActions, CoreVendorActions } from "./VendorActions";
import { defaultImages } from "./style";
import {ExtensionProvider} from "./Context/ExtensionContext";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


const bottomMenuStyle = {
    borderRadius: 0,
    marginTop: 0
};

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


const views = {
    Vendor: { extension: { _exclude: [] } },
    Listing: { vendor: { extension: { _only: ['id'] }}},
    default: {}
};


const leftColumn = {
    Vendor: (props) => (
        <React.Fragment>

            <PreviewProvider type={'Vendor'} id={props.id}>
                <ObjectImage/>
            </PreviewProvider>

            <ObjectProperties only={['name', 'url', 'image_url', 'ext_id', 'avg_shipping', 'avg_tax', 'extra']}/>

            <DocumentContext.Consumer>
                { ({ doc }) => {
                    let extId;
                    try {
                        extId = doc.extension.id;
                    } catch (e) {
                        extId = undefined;
                    }

                    return (
                        <ExtensionProvider extId={extId}>
                            <CoreVendorActions/>
                            <VendorActions/>
                        </ExtensionProvider>
                    )
                }}
            </DocumentContext.Consumer>

        </React.Fragment>
    ),

    Listing: (props) => (
        <React.Fragment>
            <PreviewProvider type={'Listing'} id={props.id}>
                <ObjectImage/>
            </PreviewProvider>

            <ObjectProperties
                only={['vendor_id', 'sku', 'title', 'brand', 'model', 'price', 'quantity', 'quantity_desc',
                'rank', 'rating', 'detail_url', 'image_url', 'extra', 'last_modified']}
            />

            <DocumentContext.Consumer>
                { ({ doc }) => {
                    let extId;

                    try {
                        extId = doc.vendor.extension.id;
                    } catch (e) {
                        extId = undefined;
                    }

                    return (
                        <ExtensionProvider extId={extId}>
                            <ListingActions/>
                            <CoreListingActions/>
                        </ExtensionProvider>
                    )
                }}
            </DocumentContext.Consumer>

        </React.Fragment>
    )
};


const mainContent = {
    Vendor: (props) => {
        const listingQuery = { vendor_id: props.id };
        const listingView = { vendor: { _only: ['name'] } };

        return (
            <React.Fragment>
                <QueryProvider type={'Listing'} query={listingQuery} view={listingView}>
                    <QueryContext.Consumer>
                        {({ type, query, view }) => (
                            <CollectionProvider {...{type, query, view}}>
                                <ObjectTable
                                    only={['sku', 'Image', 'Summary', 'price']}
                                    select
                                />
                            </CollectionProvider>
                        )}
                    </QueryContext.Consumer>
                </QueryProvider>
            </React.Fragment>
        )
    },

    Listing: (props) => (
        <React.Fragment>
            <ListingDetails/>
            <SimilarProvider id={props.id} view={{ vendor: { _only: ['name'] } }}>
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
    )
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export default class ObjectView extends React.Component {

    constructor (props) {
        super(props);
        this.state = { leftColumnRef: undefined }
    }

    render ()  {
        let { type, id } = this.props.match.params;
        ({ type, id } = { type, id: parseInt(id) });

        const view = views[type] || views.default;
        const leftColumnElement = React.createElement(leftColumn[type], { type, id });
        const mainContentElement = React.createElement(mainContent[type], { type, id });

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
                        </Menu>
                    )}
                </DocumentContext.Consumer>
                <Container fluid style={{ paddingLeft: '5em', paddingRight: '5em', paddingBottom: '5em' }}>
                    <Grid columns={2}>
                        <Grid.Column width={4}>
                            {leftColumnElement}
                        </Grid.Column>
                        <Grid.Column width={12}>
                            {mainContentElement}
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