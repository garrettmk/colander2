import React from "react";
import { Grid, Segment, Image, Header, Button, Message, Table, Tab, Divider, List, Pagination,
Checkbox, Select, Input, Icon, Search, Item } from "semantic-ui-react";

import { asCount, asCurrency, asPercent } from "./App";
import {ObjectContext, CollectionContext, ObjectProvider, CollectionProvider, QueryProvider, QueryContext} from "./Objects";
import update from "immutability-helper/index";
import forms from "./Forms";
import Autoform from "./Autoform";
import Colander from "./colander";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


const defaultImages = {
    vendor: 'https://imgplaceholder.com/128x128/cccccc/757575/fa-globe',
    customer: 'https://imgplaceholder.com/128x128/cccccc/757575/ion-android-person',
    extension: 'https://imgplaceholder.com/128x128/cccccc/757575/fa-gears'
};


const detailFormats = {
    listing: {
        id: { label: 'ID', attr: 'id' },
        header: { label: 'header', attr: 'title' },
        subheader: { label: 'subheader', attr: 'detail_url' },
        image_url: { label: 'Image URL', attr: 'image_url', value: lst => lst.vendor ? lst.vendor.name : 'n/a' },
        sku: { label: 'SKU', attr: 'sku' },
        brand: { label: 'Brand', attr: 'brand' },
        model: { label: 'Model', attr: 'model' },
        price: { label: 'Price', attr: 'price', format: { textAlign: 'right' }, value: lst => asCurrency(lst.price) },
        quantity: { label: 'Quantity', attr: 'quantity', value: lst => asCount(lst.quantity) },
        category: { label: 'Category', value: lst => lst.extra ? lst.extra.category : 'n/a' },
        rank: { label: 'Rank', attr: 'rank', value: lst => asCount(lst.rank) },
        rating: { label: 'Rating', attr: 'rating', value: lst => asPercent(lst.rating) },
        image: { label: 'Image', value: lst => <Image size={'tiny'} src={lst.image_url}/> },
        title: { label: 'Title', attr: 'title' }
    },
    vendor: {
        id: { label: 'ID', attr: 'id' },
        header: { label: 'header', attr: 'name' },
        subheader: { label: 'subheader', attr: 'url' },
        image_url: { label: 'Image URL', attr: 'image_url', value: vnd => vnd.image_url || defaultImages.vendor },
        url: { label: 'URL', attr: 'url', value: vnd => vnd.url || '(no website )' },
        extension: { label: 'Extension', attr: 'ext_id', value: vnd => vnd.ext ? vnd.ext.name : 'n/a' },
        avg_shipping: { label: 'Avg. Shipping', attr: 'avg_shipping', value: vnd => asPercent(vnd.avg_shipping)},
        avg_tax: { label: 'Avg. Tax', attr: 'avg_tax', value: vnd => asPercent(vnd.avg_tax)},
        listings: { label: 'Total listings', value: vnd => vnd.listings ? asCount(vnd.listings.total) : 'n/a'},
    },
    extension: {
        header: { label: 'header', attr: 'name', value: ext => ext.name || '(unnamed)' },
        subheader: { label: 'subheader', attr: 'module', value: ext => 'ext.' + ext.module },
        image_url: { label: 'Image URL', value: ext => defaultImages.extension },
        url: { label: 'URL', value: ext => 'ext.' + ext.module },
        exports: { label: 'Exports', value: ext => ext.exports ? <List items={Object.keys(ext.exports)}/> : 'n/a' },
    }
};

function formatObject(obj = {}, options) {
    const { type = obj.type, only = Object.keys(detailFormats[type]) } = options;

    if (!type || !obj)
        return {};

    const colFormats = detailFormats[type];
    let formatted = {};
    only.map(col => {
        const { label, attr, value, format = {} } = colFormats[col];
        formatted[col] = {
            label,
            attr,
            format,
            value: value ? value(obj) : obj[attr]
        }
    });

    return formatted;
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function ExtraPopup (props) {
    const { data } = props;
    return (
        <Popup trigger={<span>...</span>}>
            <pre>{JSON.stringify(data, null, '  ')}</pre>
        </Popup>
    )
}

function TitlePopup (props) {
    const { header, subheader } = props;
    const headerOpts = {
            dividing: true,
            style: {
                whiteSpace: 'nowrap',
                textOverflow: 'ellipsis',
                overflow: 'hidden',
                display: 'block',
            }
        };

    const trigger = (
        <Header {...headerOpts}>
            {header}
            <Header.Subheader>
                {subheader}
            </Header.Subheader>
        </Header>
    );

    return (
        <Popup trigger={trigger}>
            <Header>
                {header}
                <Header.Subheader>
                    {subheader}
                </Header.Subheader>
            </Header>
        </Popup>
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


const headerOpts = {
    style: {
        whiteSpace: 'nowrap',
        textOverflow: 'ellipsis',
        overflow: 'hidden',
        display: 'block',
    }
};


const headerImgOpts = {
    size: 'small',
    centered: true,
    rounded: true,
    style: {
        display: 'block'
    }
};


function ObjectHeader (props) {
    return (
        <ObjectContext.Consumer>
            {({ type, original }) => {
                if (!type || !original)
                    return <React.Fragment/>;

                const {image_url, url, header, subheader} = formatObject(original, {
                    only: ['image_url', 'url', 'header', 'subheader']
                });

                return (
                    <React.Fragment>
                        <Image src={image_url.value} href={url.value} {...headerImgOpts}/>
                        <Header {...headerOpts}>
                            {header.value}
                            <Header.Subheader>
                                {subheader.value}
                            </Header.Subheader>
                        </Header>
                    </React.Fragment>
                )
            }}
        </ObjectContext.Consumer>
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function ObjectSummaryTable (props) {
    const { only } = props;

    return (
        <ObjectContext.Consumer>
            {({ type, original }) => {
                if (!type || !original)
                    return <React.Fragment/>;

                const fmt = formatObject(original, { only });

                return (
                    <Table basic={'very'}>
                        <Table.Body>
                            {Object.keys(fmt).map(col => {
                                const { label, value } = fmt[col];
                                return <Table.Row key={col}>
                                    <Table.Cell>
                                        <Header size={'tiny'}>
                                            {label}
                                        </Header>
                                    </Table.Cell>
                                    <Table.Cell>
                                        {value}
                                    </Table.Cell>
                                </Table.Row>
                            })}
                        </Table.Body>
                    </Table>
                );
            }}
        </ObjectContext.Consumer>
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function ObjectDetailsEditor (props) {
    return (
        <ObjectContext.Consumer>
            {({ type, original, edits, errors, edit }) => {
                const form = forms[type]({
                    data: update(original, {$merge: edits}),
                    onChange: edit,
                    errors: errors
                });

                return (
                    <div style={{ paddingTop: '1em' }}>
                        {form}
                        <Message error hidden={_.isEmpty(errors)}>
                            {Object.keys(errors).map(err => <li key={err}><b>{err}:</b> {errors[err]}</li>)}
                        </Message>
                    </div>
                );
            }}
        </ObjectContext.Consumer>
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


const editButtonOpts = {
    compact: true,
    circular: true,
    color: 'blue',
    icon: 'edit',
    style: {
        position: 'absolute',
        top: 0,
        right: 0
    }
};


export class ObjectSummary extends React.Component {

    constructor (props) {
        super(props);
        this.state = {
            editing: false
        }
    }

    render () {
        const { editing } = this.state;
        const { type, readonly, headeronly, only } = this.props;

        return (
            <ObjectContext.Consumer>
                {({ loading, edit }) => {
                    return (
                        <Segment raised loading={loading}>
                            <div style={{ position: 'relative' }}>
                                <ObjectHeader type={type}/>
                                {readonly || headeronly || !edit
                                    ? <React.Fragment/>
                                    : <Button
                                        onClick={() => this.setState({editing: !editing})}
                                        basic={!editing}
                                        {...editButtonOpts}
                                    />
                                }
                            </div>
                            {headeronly
                                ? <React.Fragment/>
                                : <React.Fragment>
                                    <Divider/>
                                    {editing
                                        ? <ObjectDetailsEditor/>
                                        : <ObjectSummaryTable only={only}/>
                                    }
                                </React.Fragment>
                            }
                        </Segment>
                    )
                }}
            </ObjectContext.Consumer>
        )
    }
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function ListingDetails () {
    return (
        <ObjectContext.Consumer>
            {({ original, loading }) => {
                const panes = [
                    { menuItem: 'Features', render: () => <Tab.Pane>{original.features}</Tab.Pane> },
                    { menuItem: 'Description', render: () => <Tab.Pane>{original.description}</Tab.Pane>}
                ];

                return (
                    <Segment raised loading={loading}>
                        <Grid columns={2}>
                            <Grid.Column width={8}>
                                <Image
                                    src={original.image_url || defaultImages.listing}
                                    href={original.detail_url}
                                    size={'large'}
                                />
                            </Grid.Column>
                            <Grid.Column width={8} stretched>
                                <Tab panes={panes}/>
                            </Grid.Column>
                        </Grid>
                    </Segment>
                )
            }}
        </ObjectContext.Consumer>
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function ObjectTable (props) {
    const { columns } = props;

    return (
        <CollectionContext.Consumer>
            {({ loadingCollection, type, items, total, page, pages, query = {},
                selection, toggleSelected }) => {

                if (!type || !items)
                    return <React.Fragment/>;

                const formattedColumns = columns.map((col, idx) => {
                    const addedStyle = {};

                    if (idx === 0)
                        addedStyle.paddingLeft = '2em';
                    if (idx === columns.length - 1)
                        addedStyle.paddingRight = '2em';

                    const direction = query._sort ? query._sort[col] : undefined;

                    let attr, label, value, format;
                    if (col === 'select') {
                        ({ attr, label, value, format } = {
                            label: 'Select',
                            value: obj => <Checkbox
                                checked={selection.has(obj.id)}
                                onChange={(e, {checked}) => updateSelection(checked ? {$add: [obj.id]} : {$remove: [obj.id]})}
                            />
                        })
                    } else {
                        ({ attr, label, value, format } = detailFormats[type][col]);
                    }

                    return {
                        attr: attr,
                        label: label,
                        value: value ? value : obj => obj[attr],
                        format: update(format || {}, {
                            sorted: {$set: direction},
                            style: style => update(style || {}, {$merge: addedStyle}),
                        }),
                    };
                });

                const handleColumnClick = idx => {
                    return () => {
                        const { attr } = formattedColumns[idx];
                        if (!attr) return;

                        const { _sort: sort = {} } = query;
                        const direction = sort[attr] === 'ascending' ? 'descending' : 'ascending';
                        updateQuery({ _sort: { [attr]: direction }})
                    }
                };

                const handleRowClick = id => {
                    return () => {
                        toggleSelected([id])
                    }
                };

                return (
                    <Segment raised loading={loadingCollection} style={{ padding: 0 }}>
                        <Table selectable sortable striped basic={'very'}>
                            <Table.Header>
                                <Table.Row>
                                    {formattedColumns.map(({ label, format }, idx) => (
                                        <Table.HeaderCell key={idx} {...format} onClick={handleColumnClick(idx)}>
                                            {label}
                                        </Table.HeaderCell>
                                    ))}
                                </Table.Row>
                            </Table.Header>
                            <Table.Body>
                                {items.map(obj => (
                                    <Table.Row key={obj.id} onClick={handleRowClick(obj.id)} active={selection.has(obj.id)}>
                                        {formattedColumns.map(({ label, value, format }) => (
                                            <Table.Cell key={label} {...format}>
                                                {value(obj)}
                                            </Table.Cell>
                                        ))}
                                    </Table.Row>
                                ))}
                            </Table.Body>

                            <QueryContext.Consumer>
                                {({ updateQuery }) => (
                                    updateQuery
                                        ? <Table.Footer>
                                            <Table.Row>
                                                <Table.HeaderCell colSpan={formattedColumns.length} textAlign={'right'}>
                                                    {total} results.
                                                    <Pagination
                                                        activePage={page || 0}
                                                        onPageChange={(e, { activePage }) => updateQuery({ _page: activePage })}
                                                        totalPages={pages || 0}
                                                    />
                                                </Table.HeaderCell>
                                            </Table.Row>
                                        </Table.Footer>

                                        : <React.Fragment/>
                                )}
                            </QueryContext.Consumer>

                        </Table>
                    </Segment>
                )
            }}
        </CollectionContext.Consumer>
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


class ActionSender extends React.Component {

    constructor(props) {
        super(props);

        this.handleParamChange = this.handleParamChange.bind(this);
        this.sendAction = this.sendAction.bind(this);

        this.state = {
            action: undefined,
            params: {}
        }
    }

    handleParamChange (data) { this.setState({ params: data }) }
    sendAction (extId) {
        return () => {
            Colander.sendTask({
                ext_id: extId,
                ...this.state
            })
        }
    }

    render () {
        const { action, params } = this.state;

        return (
            <ObjectContext.Consumer>
                {({ original, loading }) => {
                    const actionChoices = original && original.exports
                        ? Object.keys(original.exports).map(exp => ({text: exp, value: exp}))
                        : [];

                    const { doc, schema } = original && original.exports && action
                        ? original.exports[action]
                        : {};

                    return (
                        <Segment raised clearing loading={loading}>
                            <ObjectHeader/>
                            <Divider/>
                            <Table basic={'very'}>
                                <Table.Body>
                                    <Table.Row>
                                        <Table.Cell>
                                            <Header size={'tiny'}>
                                                Action
                                            </Header>
                                        </Table.Cell>
                                        <Table.Cell>
                                            <Select
                                                fluid
                                                placeholder={'Select an action'}
                                                options={actionChoices}
                                                loading={loading}
                                                value={action}
                                                onChange={(e, { value }) => this.setState({ action: value })}
                                            />
                                        </Table.Cell>
                                    </Table.Row>
                                    {schema
                                        ? <Autoform tablerows
                                            schema={schema}
                                            data={params}
                                            onChange={this.handleParamChange}
                                        />
                                        : <React.Fragment/>
                                    }
                                </Table.Body>
                            </Table>
                            {schema
                                ? <React.Fragment>
                                    <Divider/>
                                    <Button
                                        floated={'right'}
                                        onClick={this.sendAction(original.id)}
                                    >
                                        Send
                                    </Button>
                                </React.Fragment>
                                : <React.Fragment/>
                            }
                        </Segment>
                    )
                }}
            </ObjectContext.Consumer>
        )
    }
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export default function ObjectView (props) {
    const { type, id } = props.match.params;

    let view = {};
    let column1, column2;
    switch (type) {
        case 'vendor':
            view = { ext: { _exclude: []} };
            column1 = (
                <React.Fragment>
                    <ObjectSummary
                        only={['id', 'extension', 'avg_shipping', 'avg_tax']}
                    />
                    <ObjectProvider child={'ext'}>
                        <ActionSender/>
                    </ObjectProvider>
                </React.Fragment>
            );
            column2 = (
                <React.Fragment>
                    <QueryProvider type={'listing'} query={{ vendor_id: id }} view={{ vendor: { _only: ['name'] } }}>
                        <QueryContext.Consumer>
                            {({ type, query, view }) => (
                                <CollectionProvider type={type} query={query} view={view}>
                                    <ObjectTable
                                        columns={['select', 'sku', 'image', 'title', 'price']}
                                    />
                                </CollectionProvider>
                            )}
                        </QueryContext.Consumer>
                    </QueryProvider>
                </React.Fragment>
            );
            break;
    }

    return (
        <ObjectProvider type={type} id={id} view={view}>
            <Grid columns={2}>
                <Grid.Column width={4}>
                    {column1}
                </Grid.Column>
                <Grid.Column width={12}>
                    {column2}
                </Grid.Column>
            </Grid>
        </ObjectProvider>
    )
}