import React from "react";
import { Grid, Segment, Image, Header, Button, Message, Table, Tab, Divider, List, Pagination,
Checkbox, Select, Input, Icon, Search, Item, Loader } from "semantic-ui-react";

import { asCount, asCurrency, asPercent } from "./App";
import {
    ObjectContext,
    PreviewContext,
    CollectionContext,
    ObjectProvider,
    CollectionProvider,
    QueryProvider,
    QueryContext,
    PreviewProvider
} from "./Objects";
import update from "immutability-helper/index";
import forms from "./Forms";
import Autoform from "./Autoform";
import Colander from "./colander";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


const defaultImages = {
    Vendor: 'https://imgplaceholder.com/128x128/cccccc/757575/fa-globe',
    Customer: 'https://imgplaceholder.com/128x128/cccccc/757575/ion-android-person',
    Extension: 'https://imgplaceholder.com/128x128/cccccc/757575/fa-gears'
};


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


function ObjectHeader () {
    return (
        <PreviewContext.Consumer>
            {({ loading, preview }) => {
                if (loading) {
                    return <Loader active={true}/>;
                } else if (!preview) {
                    return <Message error>No data :(</Message>;
                } else {
                    return (
                        <React.Fragment>
                            <Image src={preview.image || defaultImages[preview.type]} href={preview.url} {...headerImgOpts}/>
                            <Header {...headerOpts}>
                                {preview.title}
                                <Header.Subheader>
                                    <a href={preview.url} target={'_blank'}>{preview.description} <Icon name={'external'}/></a>
                                </Header.Subheader>
                            </Header>
                        </React.Fragment>
                    )
                }
            }}
        </PreviewContext.Consumer>
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
                                <ObjectHeader/>
                                {readonly || headeronly || !edit
                                    ? <React.Fragment/>
                                    : <Button
                                        onClick={() => this.setState({editing: !editing})}
                                        basic={!editing}
                                        {...editButtonOpts}
                                    />
                                }
                            </div>
                            {/*{headeronly*/}
                                {/*? <React.Fragment/>*/}
                                {/*: <React.Fragment>*/}
                                    {/*<Divider/>*/}
                                    {/*{editing*/}
                                        {/*? <ObjectDetailsEditor/>*/}
                                        {/*: <ObjectSummaryTable only={only}/>*/}
                                    {/*}*/}
                                {/*</React.Fragment>*/}
                            {/*}*/}
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
        case 'Vendor':
            view = { ext: { _exclude: []} };
            column1 = (
                <React.Fragment>
                    <ObjectSummary
                        only={['id', 'extension', 'avg_shipping', 'avg_tax']}
                    />
                    {/*<ObjectProvider child={'ext'}>*/}
                        {/*<ActionSender/>*/}
                    {/*</ObjectProvider>*/}
                </React.Fragment>
            );
            column2 = (
                <React.Fragment>
                    <QueryProvider type={'Listing'} query={{ vendor_id: id }} view={{ vendor: { _only: ['name'] } }}>
                        <QueryContext.Consumer>
                            {({ type, query, view }) => (
                                <CollectionProvider type={type} query={query} view={view}>
                                    {/*<ObjectTable*/}
                                        {/*columns={['select', 'sku', 'image', 'title', 'price']}*/}
                                    {/*/>*/}
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
            <PreviewProvider type={type} id={id}>
                <Grid columns={2}>
                    <Grid.Column width={4}>
                        {column1}
                    </Grid.Column>
                    <Grid.Column width={12}>
                        {column2}
                    </Grid.Column>
                </Grid>
            </PreviewProvider>
        </ObjectProvider>
    )
}