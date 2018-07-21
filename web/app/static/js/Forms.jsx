import React from "react";
import { Form, Grid, Image } from "semantic-ui-react";
import { ExtensionSelector, ActionSelector, VendorSelector } from "./Selectors";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


const states = [ 'AL', 'AK', 'AS', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FM', 'FL', 'GA', 'GU', 'HI', 'ID', 'IL',
    'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MH', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM',
    'NY', 'NC', 'ND', 'MP', 'OH', 'OK', 'OR', 'PW', 'PA', 'PR', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VI', 'VA',
    'WA', 'WV', 'WI', 'WY' ];


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export class JSONInput extends React.Component {

    constructor (props) {
        super(props);

        this.handleChange = this.handleChange.bind(this);

        this.state = {
            text: '',
            data: {},
            error: undefined,
        }
    }

    handleChange (e, { value }) {
        const { name, onChange } = this.props;
        try {
            const data = JSON.parse(value);
            this.setState({ text: value, data: data, error: undefined });
            onChange ? onChange(e, { name, value: data }) : null;
        }
        catch (error) {
            this.setState({text: value, error: error})
        }
    }

    render () {
        const {text, error: jsonError} = this.state;
        const {value, onChange, error, form, ...childProps} = this.props;

        const elem = Form.TextArea;

        return React.createElement(elem, {
            value: text,
            error: Boolean(jsonError || error),
            onChange: this.handleChange,
            ...childProps
        });
    }
}


export function TaskForm (props) {
    const { data, onChange, errors } = props;

    return (
        <Form>
            <Form.Input
                label={'Name'}
                type={'text'}
                value={data.name || ''}
                placeholder={'Task name'}
                name={'name'}
                onChange={onChange}
                error={'name' in errors}
            />
            <ExtensionSelector
                form
                label={'Extension'}
                value={data.ext_id}
                name={'ext_id'}
                onChange={onChange}
                error={'ext_id' in errors}
            />
            <ActionSelector
                form
                label={'Action'}
                extId={data.ext_id}
                value={data.action}
                placeholder={'Action'}
                name={'action'}
                onChange={onChange}
                error={'action' in errors}
            />
            <JSONInput
                label={'Parameters'}
                value={data.params}
                placeholder={'{\n\t"args": {},\n\t"kwargs": {}\n}'}
                name={'params'}
                onChange={onChange}
                error={'params' in errors}
            />
        </Form>
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export function VendorForm (props) {
    const { data, onChange, errors } = props;

    return (
        <Form>
            <Form.Input
                label={'Name'}
                type={'text'}
                value={data.name || ''}
                placeholder={'ACME, Inc.'}
                name={'name'}
                onChange={onChange}
                error={'name' in errors}
            />
            <Form.Input
                label={'Website'}
                type={'url'}
                value={data.url || ''}
                placeholder={'http://www.acme.com'}
                name={'url'}
                onChange={onChange}
                error={'url' in errors}
            />
            <Form.Input
                label={'Image'}
                type={'url'}
                value={data.image_url || ''}
                placeholder={'http://www.acme.com/logo.png'}
                name={'image_url'}
                onChange={onChange}
                error={'image_url' in errors}
            />
            <ExtensionSelector
                form
                label={'Extension'}
                value={data.ext_id}
                name={'ext_id'}
                onChange={onChange}
                error={'ext_id' in errors}
            />
        </Form>
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export function CustomerForm (props) {
    const { data, onChange, errors } = props;

    return (
        <Form>
            <Form.Input
                label={'Name'}
                type={'text'}
                value={data.name || ''}
                placeholder={'John Doe'}
                name={'name'}
                onChange={onChange}
                error={'name' in errors}
            />
            <Form.Input
                label={'Email'}
                type={'text'}
                value={data.email || ''}
                placeholder={'johndoe@email.com'}
                name={'email'}
                onChange={onChange}
                error={'email' in errors}
            />
            <Form.Input
                label={'Image'}
                type={'url'}
                value={data.image_url || ''}
                placeholder={'Avatar image'}
                name={'image_url'}
                onChange={onChange}
                error={'image_url' in errors}
            />
            <Form.Input
                label={'City'}
                type={'text'}
                value={data.city || ''}
                placeholder={'Smallville'}
                name={'city'}
                onChange={onChange}
                error={'city' in errors}
            />
            <Form.Dropdown
                options={states.map(state => {return {text: state, value: state}})}
                label={'State'}
                value={data.state || ''}
                name={'state'}
                onChange={onChange}
                error={'state' in errors}
            />
            <Form.Input
                label={'ZIP code'}
                type={'text'}
                value={data.zip}
                placeholder={'12345'}
                name={'zip'}
                onChange={onChange}
                error={'zip' in errors}
            />
        </Form>
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export function ListingForm (props) {
    const { data, onChange, errors } = props;

    return (
        <Form>
            <Form.Input
                label={'Title'}
                type={'text'}
                value={data.title || ''}
                placeholder={'Mega Product 9000'}
                name={'title'}
                onChange={onChange}
                error={'title' in errors}
            />
            <Form.Group widths={'equal'}>
                <VendorSelector
                    form
                    label={'Vendor'}
                    value={data.vendor_id}
                    onChange={onChange}
                    error={'vendor_id' in errors}
                />
                <Form.Input
                    label={'SKU'}
                    type={'text'}
                    value={data.sku || ''}
                    placeholder={'ABC-1234'}
                    name={'sku'}
                    onChange={onChange}
                    error={'sku' in errors}
                />
            </Form.Group>
            <Form.Group widths={'equal'}>
                <Form.Input
                    label={'Brand'}
                    type={'text'}
                    value={data.brand || ''}
                    placeholder={'Acme Products'}
                    name={'brand'}
                    onChange={onChange}
                    error={'brand' in errors}
                />
                <Form.Input
                    label={'Model'}
                    type={'text'}
                    value={data.model || ''}
                    placeholder={'MEGA-9K'}
                    name={'model'}
                    onChange={onChange}
                    error={'model' in errors}
                />
            </Form.Group>
            <Form.Group widths={'equal'}>
                <Form.Input
                    label={'Quantity'}
                    icon={'hashtag'}
                    iconPosition={'left'}
                    type={'number'}
                    value={data.quantity || 1}
                    placeholder={'1'}
                    name={'quantity'}
                    onChange={onChange}
                    error={'quantity' in errors}
                />
                <Form.Input
                    label={'Price'}
                    icon={'dollar'}
                    iconPosition={'left'}
                    type={'number'}
                    value={data.price || ''}
                    onChange={onChange}
                    error={'price' in errors}
                />
            </Form.Group>
            <Grid columns={2} divided>
                <Grid.Row stretched>
                    <Grid.Column width={6}>
                        <Image
                            src={data.image_url}
                            bordered
                            rounded
                            style={{ maxHeight: '100%', maxWidth: '100%' }}
                        />
                    </Grid.Column>
                    <Grid.Column width={10}>
                        <Form.Input
                            label={'Detail page'}
                            icon={'globe'}
                            iconPosition={'left'}
                            type={'url'}
                            value={data.detail_url || ''}
                            onChange={onChange}
                            error={'detail_url' in errors}
                        />
                        <Form.Input
                            label={'Image'}
                            icon={'globe'}
                            iconPosition={'left'}
                            type={'url'}
                            value={data.image_url || ''}
                            onChange={onChange}
                            error={'image_url' in errors}
                        />
                    </Grid.Column>
                </Grid.Row>
            </Grid>
        </Form>
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export function ExtensionForm (props) {
    const {data, onChange, errors} = props;

    return (
        <Form>
            <Form.Input
                label={'Name'}
                type={'text'}
                value={data.name || ''}
                placeholder={'Extendonator'}
                name={'name'}
                onChange={onChange}
                error={'name' in errors}
            />
            <Form.Input
                label={'Module'}
                type={'text'}
                value={data.module || ''}
                placeholder={'extendo'}
                name={'module'}
                onChange={onChange}
                error={'module' in errors}
            />
        </Form>
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////




const forms = {
    task: TaskForm,
    vendor: VendorForm,
    customer: CustomerForm,
    listing: ListingForm,
    extension: ExtensionForm
};

export default forms;
